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
    if query is None:
        experiments = get_experiments()
    else:
        experiments = get_experiments(
            experiment_name=query.experiment_name, 
            date=query.date,
            limit=query.limit
        )

    if not experiments:
        raise HTTPException(status_code=404, detail="No experiments found")
    
    return experiments