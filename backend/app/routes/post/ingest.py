from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.repositories.experiments import insert_experiment, insert_experiments_batch
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
def ingest_experiment(request):
    """
    Ingest one or more experiment events.
    Accepts either a single object or a list of objects.
    """
    try:
        if isinstance(request, list):
            experiments = [Experiment(**item) if isinstance(item, dict) else Experiment(**item.dict()) for item in request]
            insert_experiments_batch(experiments)
        else:
            # FastAPI parses body as dict or pydantic model
            if isinstance(request, dict):
                experiment = Experiment(**request)
            else:
                experiment = Experiment(**request.dict())
            insert_experiment(experiment)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))