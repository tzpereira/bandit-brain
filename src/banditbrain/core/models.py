from pydantic import BaseModel


class Experiment(BaseModel):
    id: int | None = None
    experiment_name: str
    variant_name: str
    impressions: int
    clicks: int
    cost: float
    event_date: str
    context: dict | None = None
    created_at: str | None = None


class Allocation(BaseModel):
    id: int | None = None
    experiment_name: str
    variant_name: str
    allocated_pct: float
    algorithm: str | None = None
    date: str
    created_at: str | None = None


class Metric(BaseModel):
    variant_name: str
    clicks: int
    total_cost: float
    impressions: int
    device: str
    location: str
    user_segment: str
    cpc: float | None = None
    cpv: float | None = None
    ctr: float
    ctr_se: float
    ctr_ci_lower: float
    ctr_ci_upper: float
