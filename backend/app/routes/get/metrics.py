from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.models import Metric
from app.repositories.experiments import get_experiments_metrics


router = APIRouter()

class MetricsQuery(BaseModel):
    experiment_name: Optional[str] = None
    date: Optional[str] = None

@router.get("/metrics", response_model=List[Metric])
def get_metrics(query: MetricsQuery = MetricsQuery()):
    """
    Returns aggregated metrics (impressions, clicks, CTR) for each variant, with optional filters.
    """
    metrics = get_experiments_metrics(
        experiment_name=query.experiment_name,
        date=query.date
    )
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics found")
    
    return metrics