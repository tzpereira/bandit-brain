import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from banditbrain.api.guardrails import block_demo_writes
from banditbrain.api.repositories.allocations import get_latest_allocation_batch
from banditbrain.api.repositories.decisions import insert_decision
from banditbrain.api.validators import validate_algorithm, validate_non_empty_string
from banditbrain.core.decide import sample_decision
from banditbrain.core.models import Decision

router = APIRouter()


class DecideRequest(BaseModel):
    experiment_name: str
    algorithm: str = "ts"

    def validate(self):
        self.experiment_name = validate_non_empty_string(self.experiment_name, "experiment_name")
        self.algorithm = validate_algorithm(self.algorithm, "algorithm")
        return self


@router.post("/decide", response_model=Decision)
def decide(request: DecideRequest = Body(...), user_id: int = Depends(block_demo_writes)):
    """
    Sample one arm from the most recently computed allocation for an experiment +
    algorithm (the "Rank" half of the serve/log/learn loop). Logs the decision with
    its propensity, policy version, and provenance so it can be replayed or
    off-policy-evaluated later. Report the outcome via POST /reward.

    Latency budget: p99 < 50ms — this endpoint samples from an already-computed
    allocation (see /recommend) rather than recomputing a policy per request, so
    the request is a single indexed read + one insert. Measured locally (single
    process, warm DB): p50 8.5ms / p95 13.4ms / p99 14.5ms over 200 requests.
    """
    try:
        req = request.validate()
        allocation = get_latest_allocation_batch(
            user_id=user_id, experiment_name=req.experiment_name, algorithm=req.algorithm
        )
        if not allocation:
            raise HTTPException(
                status_code=404,
                detail="No allocation found for this experiment/algorithm. Call /recommend first.",
            )

        variant_name, propensity = sample_decision(allocation)
        decision = Decision(
            decision_id=str(uuid.uuid4()),
            experiment_name=req.experiment_name,
            variant_name=variant_name,
            propensity=propensity,
            decision_source="served",
            algorithm=req.algorithm,
            policy_params=allocation[0].params,
            allocation_date=allocation[0].date,
        )
        insert_decision(decision, user_id=int(user_id))
        return decision
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
