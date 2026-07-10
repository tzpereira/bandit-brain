from fastapi import APIRouter, Depends, HTTPException

from banditbrain.api.jwt_auth import verify_token
from banditbrain.api.repositories.experiments import get_experiments
from banditbrain.core.models import Experiment

router = APIRouter()


@router.get("/experiments", response_model=list[Experiment])
def list_experiments(
    experiment_name: str | None = None,
    date: str | None = None,
    limit: int | None = None,
    user_id: int = Depends(verify_token),
):
    """
    List experiments, optionally filtered by experiment_name and date.
    """
    experiments = get_experiments(user_id=user_id, experiment_name=experiment_name, date=date, limit=limit)

    if not experiments:
        raise HTTPException(status_code=404, detail="No experiments found")

    return experiments
