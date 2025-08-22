from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.repositories.experiments import get_experiments_by_name_and_date, get_experiments
from app.models import Experiment
from app.utils import serialize_row

router = APIRouter()

class ExperimentsQuery(BaseModel):
    experiment_name: Optional[str] = None
    date: Optional[str] = None

@router.get("/experiments", response_model=List[Experiment])
def list_experiments(query: ExperimentsQuery = None):
    """
    List experiments, optionally filtered by experiment_name and date.
    """
    if query and query.experiment_name and query.date:
        data = get_experiments_by_name_and_date(query.experiment_name, query.date)
    else:
        rows, columns = get_experiments()
        data = [serialize_row(row, columns) for row in rows]
    if not data:
        raise HTTPException(status_code=404, detail="No experiments found")
    # Ensure each item is a dict before creating Experiment
    return [Experiment(**row_dict) for row_dict in data if isinstance(row_dict, dict)]