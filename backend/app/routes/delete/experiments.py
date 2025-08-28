from fastapi import APIRouter, HTTPException, status, Depends
from app.utils.jwt_auth import verify_token
from app.repositories.experiments import delete_experiments


router = APIRouter()

@router.delete("/experiments", status_code=status.HTTP_204_NO_CONTENT)
def delete_experiments_route(user_id: int = Depends(verify_token)):
    """
    Delete experiments records from the database.
    """
    try:
        delete_experiments(user_id=user_id)
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
