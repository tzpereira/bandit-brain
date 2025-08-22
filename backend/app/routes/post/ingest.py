from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.repositories.experiments import insert_experiment
from app.models import Experiment

router = APIRouter()

class IngestRequest(BaseModel):
    experiment_name: str
    variant_name: str
    impressions: int
    clicks: int
    event_date: str
    context: dict = {}

@router.post("/ingest", response_model=dict)
def ingest_experiment(request: IngestRequest):
    """
    Ingest a new experiment event.
    """
    try:
        # Create an Experiment object for validation and persistence
        experiment = Experiment(**request.dict())
        insert_experiment(experiment)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))