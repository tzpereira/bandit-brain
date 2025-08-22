from fastapi import APIRouter, HTTPException, Header
from app.repositories.experiments import get_experiments
from app.repositories.experiments import insert_experiment
from app.models import Experiment
from app.utils import serialize_row

experiments_router = APIRouter()
ingest_router = APIRouter()

@experiments_router.get("/experiments")
def list_experiments(limit: int = 1000):
    rows, columns = get_experiments(limit)
    data = [Experiment(**serialize_row(row, columns)) for row in rows]
    return data

@ingest_router.post("/ingest")
def ingest_experiment(data: Experiment, content_type: str = Header(...)):
    if content_type != "application/json":
        raise HTTPException(status_code=415, detail="Unsupported Media Type")
    try:
        insert_experiment(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
