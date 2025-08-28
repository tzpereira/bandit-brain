from fastapi import APIRouter, HTTPException, status, Depends
from app.utils.jwt_auth import verify_token
from app.repositories.allocations import delete_allocations


router = APIRouter()

@router.delete("/allocations", status_code=status.HTTP_204_NO_CONTENT)
def delete_allocations_route(user_id: int = Depends(verify_token)):
    """
    Delete allocations records from the database.
    """
    try:
        delete_allocations(user_id=user_id)
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
