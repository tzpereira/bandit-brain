from fastapi import APIRouter
from app.repositories.allocations import get_allocations
from app.models import Allocation
from app.utils import serialize_row

router = APIRouter()

@router.get("/allocations")
def list_allocations(limit: int = 10):
    rows, columns = get_allocations(limit)
    allocations = [Allocation(**serialize_row(row, columns)) for row in rows]
    return allocations
