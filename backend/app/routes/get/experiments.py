from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.repositories.experiments import get_experiments
from app.models import Experiment
from app.utils import serialize_row


router = APIRouter()

class ExperimentsQuery(BaseModel):
    experiment_name: Optional[str] = None
    date: Optional[str] = None
    limit: Optional[int] = None

@router.get("/experiments", response_model=List[Experiment])
def list_experiments(query: ExperimentsQuery = None):
    """
    List experiments, optionally filtered by experiment_name and date.
    """
    experiments = get_experiments(
        query.experiment_name, 
        query.date,
        query.limit
    )

    if not experiments:
        raise HTTPException(status_code=404, detail="No experiments found")
    
    return experiments