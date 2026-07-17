import numpy as np
import pytest

from banditbrain.core.models import Metric
from banditbrain.core.policies import EpsilonGreedyBandit, SoftmaxBandit, project_to_floor_cap


def make_metric(variant: str, impressions: int, clicks: int) -> Metric:
    ctr = clicks / impressions if impressions else 0.0
    return Metric(
        variant_name=variant,
        clicks=clicks,
        total_cost=1.0,
        impressions=impressions,
        device="mobile",
        location="BRA",
        user_segment="new_user",
        ctr=ctr,
        ctr_se=0.01,
        ctr_ci_lower=max(ctr - 0.02, 0.0),
        ctr_ci_upper=ctr + 0.02,
    )


# --- project_to_floor_cap (pure function) -----------------------------------


def test_project_no_op_when_already_feasible():
    probs = np.array([0.7, 0.3])
    floors = np.array([0.0, 0.0])
    caps = np.array([1.0, 1.0])
    result = project_to_floor_cap(probs, floors, caps)
    np.testing.assert_allclose(result, probs)


def test_project_lifts_starved_arm_to_its_floor():
    # C's raw share (0) is below its 0.1 floor; the floor must be honored.
    probs = np.array([0.9, 0.1, 0.0])
    floors = np.array([0.0, 0.0, 0.1])
    caps = np.array([1.0, 1.0, 1.0])
    result = project_to_floor_cap(probs, floors, caps)
    assert result[2] == pytest.approx(0.1)
    assert result.sum() == pytest.approx(1.0)


def test_project_caps_a_dominant_arm():
    probs = np.array([0.95, 0.05])
    floors = np.array([0.0, 0.0])
    caps = np.array([0.8, 1.0])
    result = project_to_floor_cap(probs, floors, caps)
    assert result[0] == pytest.approx(0.8)
    assert result[1] == pytest.approx(0.2)


def test_project_preserves_relative_preference_among_free_arms():
    # A and B both uncapped/unfloored; their 3:1 raw ratio should survive after
    # C is lifted to its floor.
    probs = np.array([0.6, 0.2, 0.0])
    floors = np.array([0.0, 0.0, 0.2])
    caps = np.array([1.0, 1.0, 1.0])
    result = project_to_floor_cap(probs, floors, caps)
    assert result[0] / result[1] == pytest.approx(0.6 / 0.2)
    assert result.sum() == pytest.approx(1.0)


def test_project_rejects_infeasible_floors():
    with pytest.raises(ValueError, match="infeasible"):
        project_to_floor_cap(np.array([0.5, 0.5]), np.array([0.6, 0.6]), np.array([1.0, 1.0]))


def test_project_rejects_infeasible_caps():
    with pytest.raises(ValueError, match="infeasible"):
        project_to_floor_cap(np.array([0.5, 0.5]), np.array([0.0, 0.0]), np.array([0.3, 0.3]))


# --- BanditPolicy integration -------------------------------------------------


def test_min_allocation_floor_is_respected_end_to_end():
    m = [make_metric("A", 1000, 500), make_metric("B", 1000, 1)]
    probs = EpsilonGreedyBandit(m, epsilon=0.0, min_allocation=0.15).allocate()
    # Raw EG with epsilon=0 would give B exactly 0; the floor must lift it to 0.15.
    assert probs[1] == pytest.approx(0.0)  # sanity: raw allocate() is unaffected
    allocations = EpsilonGreedyBandit(m, epsilon=0.0, min_allocation=0.15).get_allocation()
    by_variant = {a.variant_name: a.allocated_pct for a in allocations}
    assert by_variant["B"] == pytest.approx(0.15)
    assert sum(by_variant.values()) == pytest.approx(1.0)


def test_max_allocation_cap_is_respected_end_to_end():
    m = [make_metric("A", 1000, 500), make_metric("B", 1000, 1)]
    allocations = EpsilonGreedyBandit(m, epsilon=0.0, max_allocation=0.7).get_allocation()
    by_variant = {a.variant_name: a.allocated_pct for a in allocations}
    assert by_variant["A"] == pytest.approx(0.7)
    assert sum(by_variant.values()) == pytest.approx(1.0)


def test_protect_the_champion_guarantees_incumbent_share():
    # B is the losing incumbent; without protection it would get ~0 traffic.
    m = [make_metric("A", 1000, 500), make_metric("B", 1000, 1)]
    allocations = SoftmaxBandit(m, tau=0.01, champion="B", champion_min_allocation=0.2).get_allocation()
    by_variant = {a.variant_name: a.allocated_pct for a in allocations}
    assert by_variant["B"] >= 0.2 - 1e-9
    assert sum(by_variant.values()) == pytest.approx(1.0)


def test_champion_protection_does_not_affect_non_champion_when_already_winning():
    m = [make_metric("A", 1000, 500), make_metric("B", 1000, 1)]
    allocations = EpsilonGreedyBandit(m, epsilon=0.0, champion="A", champion_min_allocation=0.2).get_allocation()
    by_variant = {a.variant_name: a.allocated_pct for a in allocations}
    assert by_variant["A"] == pytest.approx(1.0)


def test_unknown_champion_raises_clear_error():
    m = [make_metric("A", 1000, 500), make_metric("B", 1000, 1)]
    with pytest.raises(ValueError, match="not among the experiment's variants"):
        EpsilonGreedyBandit(m, champion="nonexistent").get_allocation()
