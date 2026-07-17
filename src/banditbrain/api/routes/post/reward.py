from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from banditbrain.api.jwt_auth import verify_token
from banditbrain.api.repositories.decisions import get_decision
from banditbrain.api.repositories.rewards import DuplicateRewardError, insert_reward
from banditbrain.api.validators import validate_binary_reward, validate_non_empty_string
from banditbrain.core.models import Reward

router = APIRouter()


class RewardRequest(BaseModel):
    decision_id: str
    reward: float = 1.0

    def validate(self):
        self.decision_id = validate_non_empty_string(self.decision_id, "decision_id")
        self.reward = validate_binary_reward(self.reward, "reward")
        return self


@router.post("/reward", response_model=Reward)
def report_reward(request: RewardRequest = Body(...), user_id: int = Depends(verify_token)):
    """
    Attribute an outcome to a decision_id logged by a prior POST /decide call —
    the "Reward" half of the serve/log/learn loop. At most one reward per decision.
    """
    try:
        req = request.validate()
        decision = get_decision(decision_id=req.decision_id, user_id=user_id)
        if decision is None:
            raise HTTPException(status_code=404, detail="Decision not found.")

        reward = Reward(decision_id=req.decision_id, reward=req.reward)
        try:
            insert_reward(reward, user_id=int(user_id))
        except DuplicateRewardError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        return reward
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
