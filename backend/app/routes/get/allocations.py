
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.repositories.allocations import get_allocations
from app.models import Allocation
from app.utils import serialize_row

router = APIRouter()

class AllocationsQuery(BaseModel):
    limit: Optional[int] = 1000

@router.get("/allocations", response_model=List[Allocation])
def list_allocations(query: AllocationsQuery = AllocationsQuery()):
    """
    List allocations with optional limit.
    """
    rows, columns = get_allocations(query.limit)
    allocations = [Allocation(**serialize_row(row, columns)) for row in rows]
    if not allocations:
        raise HTTPException(status_code=404, detail="No allocations found")
    return allocations