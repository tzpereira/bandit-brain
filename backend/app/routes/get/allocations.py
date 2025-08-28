from fastapi import APIRouter, HTTPException, Depends
from app.utils.jwt_auth import verify_token
from typing import List, Optional
from app.repositories.allocations import get_allocations
from app.models import Allocation

router = APIRouter()

@router.get("/allocations", response_model=List[Allocation])
def list_allocations(
    experiment_name: Optional[str] = None,
    date: Optional[str] = None,
    algorithm: Optional[str] = None,
    limit: Optional[int] = None,
    user_id: int = Depends(verify_token)
):
    """
    List allocations with optional filters: experiment_name, date, and limit.
    """
    allocations = get_allocations(
        user_id=user_id,
        experiment_name=experiment_name,
        date=date,
        algorithm=algorithm,
        limit=limit
    )

    if not allocations:
        raise HTTPException(status_code=404, detail="No allocations found")
    
    return allocations
