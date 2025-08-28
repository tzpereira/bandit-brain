from fastapi import APIRouter, HTTPException, Depends
from app.utils.jwt_auth import verify_token
from typing import List, Optional
from app.repositories.experiments import get_experiments
from app.models import Experiment

router = APIRouter()

@router.get("/experiments", response_model=List[Experiment])
def list_experiments(
    experiment_name: Optional[str] = None,
    date: Optional[str] = None,
    limit: Optional[int] = None,
    user_id: int = Depends(verify_token)
    ):
    """
    List experiments, optionally filtered by experiment_name and date.
    """
    experiments = get_experiments(
        user_id=user_id,
        experiment_name=experiment_name,
        date=date,
        limit=limit
    )

    if not experiments:
        raise HTTPException(status_code=404, detail="No experiments found")
    
    return experiments
