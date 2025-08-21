from pydantic import BaseModel
from typing import Optional

class Experiment(BaseModel):
    id: Optional[int]
    experiment_name: str
    variant_name: str
    impressions: int
    clicks: int
    event_date: str
    context: Optional[dict]
    created_at: Optional[str]

class Allocation(BaseModel):
    id: Optional[int]
    experiment_name: str
    variant_name: str
    allocated_pct: float
    date: str
    created_at: Optional[str]
