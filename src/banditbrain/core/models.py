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
    params: dict | None = None
    date: str
    created_at: str | None = None


class Decision(BaseModel):
    """
    A single served decision: one arm sampled from a stored Allocation batch.

    Carries everything needed to replay or off-policy-evaluate the decision later:
    the chosen arm, its propensity P(arm | state), the policy version (algorithm +
    params) and batch date it was sampled from, and its provenance.
    """

    decision_id: str
    experiment_name: str
    variant_name: str
    propensity: float
    decision_source: str  # "served" (Bandit Brain sampled it) | "byo" (client-supplied)
    algorithm: str
    policy_params: dict | None = None
    allocation_date: str
    created_at: str | None = None


class Reward(BaseModel):
    """
    An outcome attributed to a decision.

    Binary for now (1.0 = converted, 0.0 = did not) to match the CTR-based Metric
    model every policy already consumes; continuous/monetary rewards are budget-aware
    allocation territory, out of scope here (see ROADMAP non-goals).
    """

    decision_id: str
    reward: float
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
