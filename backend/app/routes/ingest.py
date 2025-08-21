from fastapi import APIRouter, Header, HTTPException
from app.models import Experiment
from app.repositories.experiments import insert_experiment

router = APIRouter()

@router.post("/ingest")
def ingest_experiment(data: Experiment, content_type: str = Header(...)):
    if content_type != "application/json":
        raise HTTPException(status_code=415, detail="Unsupported Media Type")
    try:
        insert_experiment(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
