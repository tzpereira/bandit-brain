import pytest

from banditbrain.api.routes.post.recommend import RecommendRequest


def test_valid_request_passes_validation():
    req = RecommendRequest(experiment_name="exp", method="ts").validate()
    assert req.method == "ts"


def test_bias_controls_omits_unset_fields():
    req = RecommendRequest(experiment_name="exp").validate()
    assert req.bias_controls() == {}


def test_bias_controls_includes_only_the_fields_that_were_set():
    req = RecommendRequest(experiment_name="exp", min_allocation=0.1, champion="A").validate()
    assert req.bias_controls() == {"min_allocation": 0.1, "champion": "A"}


def test_rejects_min_allocation_above_max_allocation():
    with pytest.raises(ValueError, match="min_allocation must not exceed max_allocation"):
        RecommendRequest(experiment_name="exp", min_allocation=0.5, max_allocation=0.2).validate()


def test_rejects_out_of_range_allocation_bound():
    with pytest.raises(ValueError, match="min_allocation must be a float between 0 and 1"):
        RecommendRequest(experiment_name="exp", min_allocation=1.5).validate()


def test_rejects_out_of_range_champion_min_allocation():
    with pytest.raises(ValueError, match="champion_min_allocation must be a float between 0 and 1"):
        RecommendRequest(experiment_name="exp", champion_min_allocation=-0.1).validate()


def test_priors_pass_through_untouched():
    req = RecommendRequest(experiment_name="exp", method="ts", priors={"A": (5.0, 2.0)}).validate()
    assert req.priors == {"A": (5.0, 2.0)}
