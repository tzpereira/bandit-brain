from fastapi import APIRouter, Depends, HTTPException, status

from banditbrain.api.jwt_auth import verify_token
from banditbrain.api.repositories.experiments import delete_experiments

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
        raise HTTPException(status_code=500, detail=str(e)) from e
