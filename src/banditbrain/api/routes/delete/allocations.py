from fastapi import APIRouter, Depends, HTTPException, status

from banditbrain.api.guardrails import block_demo_writes
from banditbrain.api.repositories.allocations import delete_allocations

router = APIRouter()


@router.delete("/allocations", status_code=status.HTTP_204_NO_CONTENT)
def delete_allocations_route(user_id: int = Depends(block_demo_writes)):
    """
    Delete allocations records from the database.
    """
    try:
        delete_allocations(user_id=user_id)
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
