from fastapi import APIRouter, HTTPException, status
from app.repositories.experiments import delete_experiments


router = APIRouter()

@router.delete("/experiments", status_code=status.HTTP_204_NO_CONTENT)
def delete_experiments_route():
    """
    Delete experiments records from the database.
    """
    try:
        delete_experiments()
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
