from fastapi import APIRouter, HTTPException, status
from app.repositories.allocations import delete_allocations


router = APIRouter()

@router.delete("/allocations", status_code=status.HTTP_204_NO_CONTENT)
def delete_allocations_route():
    """
    Delete allocations records from the database.
    """
    try:
        delete_allocations()
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
