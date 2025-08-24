from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, RootModel
from typing import List
from app.repositories.experiments import insert_experiments_batch
from app.models import Experiment
from app.validators.validation import (
    validate_non_empty_string,
    validate_non_negative_int,
    validate_non_negative_float,
    validate_date_string,
    validate_context_dict
)

router = APIRouter()

class IngestRequest(BaseModel):
    experiment_name: str
    variant_name: str
    impressions: int
    clicks: int
    cost: float
    event_date: str
    context: dict = {}

    def validate(self):
        self.experiment_name = validate_non_empty_string(self.experiment_name, 'experiment_name')
        self.variant_name = validate_non_empty_string(self.variant_name, 'variant_name')
        self.impressions = validate_non_negative_int(self.impressions, 'impressions')
        self.clicks = validate_non_negative_int(self.clicks, 'clicks')
        self.cost = validate_non_negative_float(self.cost, 'cost')
        self.event_date = validate_date_string(self.event_date, 'event_date')
        self.context = validate_context_dict(self.context)
        return self

class IngestBatch(RootModel[List[IngestRequest]]):
    pass

def to_ingest_request(item):
    if isinstance(item, dict):
        return IngestRequest(**item)
    elif isinstance(item, IngestRequest):
        return item
    else:
        return IngestRequest(**item.dict())

@router.post("/ingest", response_model=dict)
def ingest_experiment(request: IngestBatch):
    """
    Ingest one or more experiment events.
    Accepts a list of objects (array JSON).
    Uses global validators for all fields and returns HTTP 422/400 for invalid data.
    """
    try:
        validated = []
        errors = []
        for idx, item in enumerate(request.root):
            try:
                obj = to_ingest_request(item)
                obj.validate()
                validated.append(obj)
            except Exception as ve:
                errors.append({"index": idx, "error": str(ve)})
        if errors:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})
        experiments = [Experiment(**obj.dict()) for obj in validated]

        # Persist experiments to the database
        insert_experiments_batch(experiments)
        
        return {"status": "success"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))