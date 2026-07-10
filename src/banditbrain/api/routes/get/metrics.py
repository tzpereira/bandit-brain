from fastapi import APIRouter, Depends, HTTPException

from banditbrain.api.jwt_auth import verify_token
from banditbrain.api.repositories.experiments import get_experiments_metrics
from banditbrain.core.models import Metric

router = APIRouter()


@router.get("/metrics", response_model=list[Metric])
def get_metrics(
    experiment_name: str | None = None,
    date: str | None = None,
    group_by_context: bool = False,
    user_id: int = Depends(verify_token),
):
    """
    Returns aggregated metrics (impressions, clicks, CTR) for each variant, with optional filters.
    """
    metrics = get_experiments_metrics(
        user_id=user_id, experiment_name=experiment_name, date=date, group_by_context=group_by_context
    )

    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics found")

    return metrics
