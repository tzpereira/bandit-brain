import pytest

from banditbrain.api.routes.post.ingest import IngestRequest


def _valid_payload(**overrides):
    payload = {
        "experiment_name": "exp",
        "variant_name": "A",
        "impressions": 1000,
        "clicks": 120,
        "cost": 1.0,
        "event_date": "2026-01-01",
        "context": {"device": "mobile"},
    }
    payload.update(overrides)
    return payload


def test_valid_event_passes_validation():
    req = IngestRequest(**_valid_payload()).validate()
    assert req.clicks == 120


def test_clicks_exceeding_impressions_is_rejected():
    with pytest.raises(ValueError, match="clicks must not exceed impressions"):
        IngestRequest(**_valid_payload(impressions=10, clicks=50)).validate()


def test_clicks_equal_to_impressions_is_allowed():
    req = IngestRequest(**_valid_payload(impressions=10, clicks=10)).validate()
    assert req.clicks == req.impressions
