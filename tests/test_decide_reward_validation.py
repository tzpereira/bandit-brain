import pytest

from banditbrain.api.routes.post.decide import DecideRequest
from banditbrain.api.routes.post.reward import RewardRequest


def test_valid_decide_request_passes_validation():
    req = DecideRequest(experiment_name="exp", algorithm="ts").validate()
    assert req.algorithm == "ts"


def test_decide_request_defaults_to_thompson_sampling():
    req = DecideRequest(experiment_name="exp").validate()
    assert req.algorithm == "ts"


def test_decide_request_rejects_unknown_algorithm():
    with pytest.raises(ValueError, match="algorithm must be one of"):
        DecideRequest(experiment_name="exp", algorithm="bogus").validate()


def test_decide_request_rejects_empty_experiment_name():
    with pytest.raises(ValueError, match="experiment_name must be a non-empty string"):
        DecideRequest(experiment_name="").validate()


def test_valid_reward_request_passes_validation():
    req = RewardRequest(decision_id="abc-123", reward=1.0).validate()
    assert req.reward == 1.0


def test_reward_request_defaults_to_positive_reward():
    req = RewardRequest(decision_id="abc-123").validate()
    assert req.reward == 1.0


def test_reward_request_rejects_non_binary_reward():
    with pytest.raises(ValueError, match="reward must be 0.0 or 1.0"):
        RewardRequest(decision_id="abc-123", reward=0.5).validate()


def test_reward_request_rejects_empty_decision_id():
    with pytest.raises(ValueError, match="decision_id must be a non-empty string"):
        RewardRequest(decision_id="").validate()
