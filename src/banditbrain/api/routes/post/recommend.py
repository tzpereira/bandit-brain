from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from banditbrain.api.jwt_auth import verify_token
from banditbrain.api.repositories.allocations import insert_allocations_batch
from banditbrain.api.repositories.experiments import get_experiments_metrics
from banditbrain.api.validators import (
    validate_algorithm,
    validate_allocation_bound,
    validate_epsilon,
    validate_non_empty_string,
    validate_non_negative_float,
)
from banditbrain.core.models import Allocation
from banditbrain.core.policies import EpsilonGreedyBandit, SoftmaxBandit, ThompsonSamplingBandit, UCBBandit

router = APIRouter()


class RecommendRequest(BaseModel):
    experiment_name: str
    date: str | None = None
    method: str = "eg"  # 'eg', 'ucb', 'ts', 'softmax'
    epsilon: float | None = 0.1
    c: float | None = 2.0
    tau: float | None = 0.1
    # Bias controls (see ROADMAP Phase 1.3): floors/caps applied after the policy
    # computes its raw preference, plus an optional "protect the champion" floor.
    min_allocation: float | None = None
    max_allocation: float | None = None
    champion: str | None = None
    champion_min_allocation: float | None = None
    # Thompson Sampling only: seed a variant's Beta posterior from history so a
    # known-good variant starts strong instead of at Beta(1, 1).
    priors: dict[str, tuple[float, float]] | None = None

    def validate(self):
        self.experiment_name = validate_non_empty_string(self.experiment_name, "experiment_name")
        self.method = validate_algorithm(self.method, "method")
        if self.epsilon is not None:
            self.epsilon = validate_epsilon(self.epsilon, "epsilon")
        if self.c is not None:
            self.c = validate_non_negative_float(self.c, "c")
        if self.tau is not None:
            self.tau = validate_non_negative_float(self.tau, "tau")
        if self.min_allocation is not None:
            self.min_allocation = validate_allocation_bound(self.min_allocation, "min_allocation")
        if self.max_allocation is not None:
            self.max_allocation = validate_allocation_bound(self.max_allocation, "max_allocation")
        if self.champion is not None:
            self.champion = validate_non_empty_string(self.champion, "champion")
        if self.champion_min_allocation is not None:
            self.champion_min_allocation = validate_allocation_bound(
                self.champion_min_allocation, "champion_min_allocation"
            )
        if (
            self.min_allocation is not None
            and self.max_allocation is not None
            and self.min_allocation > self.max_allocation
        ):
            raise ValueError("min_allocation must not exceed max_allocation.")
        return self

    def bias_controls(self) -> dict:
        controls = {}
        if self.min_allocation is not None:
            controls["min_allocation"] = self.min_allocation
        if self.max_allocation is not None:
            controls["max_allocation"] = self.max_allocation
        if self.champion is not None:
            controls["champion"] = self.champion
        if self.champion_min_allocation is not None:
            controls["champion_min_allocation"] = self.champion_min_allocation
        return controls


@router.post("/recommend", response_model=list[Allocation])
def recommend_allocation(request: RecommendRequest = Body(...), user_id: int = Depends(verify_token)):
    """
    Returns recommended allocation for experiment variants using the chosen algorithm.
    """
    try:
        req = request.validate()
        metrics = get_experiments_metrics(user_id=user_id, experiment_name=req.experiment_name, date=req.date)
        if not metrics:
            raise HTTPException(status_code=404, detail="No metrics found for the specified experiment.")

        bias_controls = req.bias_controls()
        if req.method == "eg":
            bandit = EpsilonGreedyBandit(
                metrics, epsilon=req.epsilon, experiment_name=req.experiment_name, date=req.date, **bias_controls
            )
        elif req.method == "ucb":
            bandit = UCBBandit(metrics, c=req.c, experiment_name=req.experiment_name, date=req.date, **bias_controls)
        elif req.method == "ts":
            bandit = ThompsonSamplingBandit(
                metrics,
                priors=req.priors,
                experiment_name=req.experiment_name,
                date=req.date,
                **bias_controls,
            )
        elif req.method == "softmax":
            bandit = SoftmaxBandit(
                metrics, tau=req.tau, experiment_name=req.experiment_name, date=req.date, **bias_controls
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid method. Use 'eg', 'ucb', 'ts' or 'softmax'.")

        allocations = bandit.get_allocation()

        # Persist allocations to the database
        insert_allocations_batch(allocations, user_id=int(user_id))
        return allocations
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
