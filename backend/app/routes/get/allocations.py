from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.repositories.allocations import get_allocations
from app.models import Allocation


router = APIRouter()

class AllocationsQuery(BaseModel):
    experiment_name: Optional[str] = None
    date: Optional[str] = None
    limit: Optional[int] = None

@router.get("/allocations", response_model=List[Allocation])
def list_allocations(query: AllocationsQuery = AllocationsQuery()):
    """
    List allocations with optional filters: experiment_name, date, and limit.
    """
    allocations = get_allocations(
        experiment_name=query.experiment_name,
        date=query.date,
        limit=query.limit
    )
    if not allocations:
        raise HTTPException(status_code=404, detail="No allocations found")
    
    return allocations