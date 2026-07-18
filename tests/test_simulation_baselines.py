import numpy as np
import pytest

from banditbrain.simulation.baselines import fixed_split_allocation, oracle_allocation, uniform_allocation


def test_uniform_allocation_splits_evenly():
    probs = uniform_allocation(4)
    np.testing.assert_allclose(probs, [0.25, 0.25, 0.25, 0.25])
    assert probs.sum() == pytest.approx(1.0)


def test_oracle_allocation_puts_everything_on_the_best_arm():
    probs = oracle_allocation(3, best_arm=1)
    np.testing.assert_allclose(probs, [0.0, 1.0, 0.0])


def test_fixed_split_allocation_favors_the_designated_arm():
    probs = fixed_split_allocation(3, favored_arm=0, favored_share=0.9)
    assert probs[0] == pytest.approx(0.9)
    assert probs[1] == pytest.approx(0.05)
    assert probs[2] == pytest.approx(0.05)
    assert probs.sum() == pytest.approx(1.0)


def test_fixed_split_allocation_rejects_out_of_range_share():
    with pytest.raises(AssertionError):
        fixed_split_allocation(2, favored_share=1.5)
