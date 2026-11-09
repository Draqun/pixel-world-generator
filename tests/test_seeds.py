import numpy as np

from pixel_world.seeds import step_rng


def test_same_inputs_same_sequence() -> None:
    a = step_rng(42, "noise").random(8)
    b = step_rng(42, "noise").random(8)
    assert np.array_equal(a, b)


def test_different_step_names_differ() -> None:
    assert not np.array_equal(step_rng(42, "noise").random(8), step_rng(42, "island").random(8))


def test_different_seeds_differ() -> None:
    assert not np.array_equal(step_rng(1, "noise").random(8), step_rng(2, "noise").random(8))


def test_call_order_does_not_matter() -> None:
    first = step_rng(7, "erosion").random(4)
    step_rng(7, "noise").random(100)  # drawing from another step in between
    again = step_rng(7, "erosion").random(4)
    assert np.array_equal(first, again)
