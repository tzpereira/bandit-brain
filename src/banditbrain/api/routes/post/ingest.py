from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, RootModel

from banditbrain.api.guardrails import block_demo_writes
from banditbrain.api.repositories.experiments import insert_experiments_batch
from banditbrain.api.validators import (
    validate_batch_size,
    validate_context_dict,
    validate_date_string,
    validate_non_empty_string,
    validate_non_negative_float,
    validate_non_negative_int,
)
from banditbrain.core.models import Experiment

router = APIRouter()

# Guardrail for a public deployment (see ROADMAP.md Phase 4): caps how much one
# request can write, independent of the raw byte-size limit enforced globally
# by BodySizeLimitMiddleware.
MAX_INGEST_BATCH_SIZE = 1000


class IngestRequest(BaseModel):
    experiment_name: str
    variant_name: str
    impressions: int
    clicks: int
    cost: float
    event_date: str
    context: dict = {}

    def validate(self):
        self.experiment_name = validate_non_empty_string(self.experiment_name, "experiment_name")
        self.variant_name = validate_non_empty_string(self.variant_name, "variant_name")
        self.impressions = validate_non_negative_int(self.impressions, "impressions")
        self.clicks = validate_non_negative_int(self.clicks, "clicks")
        self.cost = validate_non_negative_float(self.cost, "cost")
        if self.clicks > self.impressions:
            raise ValueError("clicks must not exceed impressions (CTR cannot be greater than 100%).")
        self.event_date = validate_date_string(self.event_date, "event_date")
        self.context = validate_context_dict(self.context)
        return self


class IngestBatch(RootModel[list[IngestRequest]]):
    pass


def to_ingest_request(item):
    if isinstance(item, dict):
        return IngestRequest(**item)
    elif isinstance(item, IngestRequest):
        return item
    else:
        return IngestRequest(**item.dict())


@router.post("/ingest", response_model=dict)
def ingest_experiment(request: IngestBatch, user_id: int = Depends(block_demo_writes)):
    """
    Ingest one or more experiment events.
    Accepts a list of objects (array JSON).
    Uses global validators for all fields and returns HTTP 422/400 for invalid data.
    """
    try:
        try:
            validate_batch_size(request.root, MAX_INGEST_BATCH_SIZE, "batch")
        except ValueError as ve:
            raise HTTPException(status_code=413, detail=str(ve)) from ve

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
        insert_experiments_batch(user_id=int(user_id), experiments=experiments)

        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
