import numpy as np

from pixel_world.island import island_mask


def test_range_edge_and_centre() -> None:
    m = island_mask(1, 128, 2.5, 0.25)
    assert m.min() >= 0 and m.max() <= 1
    for edge in (m[0], m[-1], m[:, 0], m[:, -1]):
        assert (edge == 0).all()
    assert m[60:68, 60:68].min() > 0.9


def test_deterministic_and_seed_dependent() -> None:
    assert np.array_equal(island_mask(1, 64, 2.5, 0.25), island_mask(1, 64, 2.5, 0.25))
    assert not np.array_equal(island_mask(1, 64, 2.5, 0.25), island_mask(2, 64, 2.5, 0.25))
