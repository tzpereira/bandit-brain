from typing import Optional
from pydantic import BaseModel

class User(BaseModel):
    id: int
    email: str
    password: str
    created_at: str

class Experiment(BaseModel):
    id: Optional[int] = None
    experiment_name: str
    variant_name: str
    impressions: int
    clicks: int
    cost: float
    event_date: str
    context: Optional[dict] = None
    created_at: Optional[str] = None

class Allocation(BaseModel):
    id: Optional[int] = None
    experiment_name: str
    variant_name: str
    allocated_pct: float
    algorithm: Optional[str] = None
    date: str
    created_at: Optional[str] = None

class Metric(BaseModel):
    variant_name: str
    clicks: int
    total_cost: float
    impressions: int
    device: str
    location: str
    user_segment: str
    cpc: Optional[float] = None
    cpv: Optional[float] = None
    ctr: float
    ctr_se: float
    ctr_ci_lower: float
    ctr_ci_upper: float