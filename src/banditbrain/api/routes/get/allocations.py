from fastapi import APIRouter, Depends, HTTPException

from banditbrain.api.jwt_auth import verify_token
from banditbrain.api.repositories.allocations import get_allocations
from banditbrain.core.models import Allocation

router = APIRouter()


@router.get("/allocations", response_model=list[Allocation])
def list_allocations(
    experiment_name: str | None = None,
    date: str | None = None,
    algorithm: str | None = None,
    limit: int | None = None,
    user_id: int = Depends(verify_token),
):
    """
    List allocations with optional filters: experiment_name, date, and limit.
    """
    allocations = get_allocations(
        user_id=user_id, experiment_name=experiment_name, date=date, algorithm=algorithm, limit=limit
    )

    if not allocations:
        raise HTTPException(status_code=404, detail="No allocations found")

    return allocations
