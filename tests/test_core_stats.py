import pytest
from hypothesis import given
from hypothesis import strategies as st

from banditbrain.core.stats import standard_error, wilson_score_interval


def test_zero_impressions_returns_maximally_uncertain_interval():
    # No data at all -> the true CTR could be anything; must not collapse to [0, 0].
    lower, upper = wilson_score_interval(clicks=0, impressions=0)
    assert (lower, upper) == (0.0, 1.0)


def test_zero_impressions_has_zero_standard_error_by_convention():
    assert standard_error(clicks=0, impressions=0) == 0.0


def test_zero_clicks_with_impressions_gives_a_narrow_low_interval_not_a_point():
    # Some data, no clicks: CTR could still plausibly be low-but-nonzero; the
    # interval should reflect that instead of collapsing to a single point.
    lower, upper = wilson_score_interval(clicks=0, impressions=1000)
    assert lower == pytest.approx(0.0, abs=1e-9)
    assert 0.0 < upper < 0.02


def test_overwhelming_evidence_gives_a_tight_interval_around_the_true_rate():
    lower, upper = wilson_score_interval(clicks=50_000, impressions=100_000)
    assert lower == pytest.approx(0.5, abs=0.01)
    assert upper == pytest.approx(0.5, abs=0.01)


def test_interval_always_contains_the_point_estimate():
    lower, upper = wilson_score_interval(clicks=120, impressions=1000)
    ctr = 120 / 1000
    assert lower <= ctr <= upper


@given(clicks=st.integers(min_value=0, max_value=10_000), impressions=st.integers(min_value=1, max_value=10_000))
def test_interval_is_always_a_valid_probability_range(clicks, impressions):
    clicks = min(clicks, impressions)  # clicks <= impressions is the schema invariant
    lower, upper = wilson_score_interval(clicks, impressions)
    assert 0.0 <= lower <= upper <= 1.0


@given(clicks=st.integers(min_value=0, max_value=10_000), impressions=st.integers(min_value=1, max_value=10_000))
def test_standard_error_is_never_negative(clicks, impressions):
    clicks = min(clicks, impressions)
    assert standard_error(clicks, impressions) >= 0.0
