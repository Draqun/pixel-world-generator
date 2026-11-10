import numpy as np

from pixel_world.water import drainage


def test_bowl_is_filled_and_routes_without_cycles() -> None:
    ground = np.array(
        [[5, 5, 4, 5, 5], [5, 3, 3, 3, 5], [5, 3, 0, 3, 5], [5, 3, 3, 3, 5], [5, 5, 5, 5, 5]],
        dtype=np.uint16,
    )
    original = ground.copy()
    sea, lake, filled, targets = drainage(ground, 0.0, 65535.0, 1.0)
    assert not sea.any()
    assert filled[2, 2] == 4 and lake[2, 2]
    assert not lake[0, 0]
    assert np.array_equal(ground, original)
    for start in range(ground.size):
        seen = set()
        cell = start
        while cell != -1:
            assert cell not in seen
            seen.add(cell)
            cell = int(targets.flat[cell])


def test_sea_connectivity_and_flat_outlets() -> None:
    ground = np.array([[0, 5, 5], [5, 0, 5], [5, 5, 5]], dtype=np.uint16)
    sea, _, _, _ = drainage(ground, 1 / 65535, 65535.0, 1.0)
    assert sea[0, 0] and sea[1, 1]  # diagonal connectivity
    ground[0, 0] = 5
    sea, _, filled, _ = drainage(ground, 1 / 65535, 65535.0, 1.0)
    assert not sea.any() and filled[1, 1] == 5
    sea, lake, filled, targets = drainage(np.zeros((3, 3), dtype=np.uint16), 0.5, 100, 1.0)
    assert not lake.any()
    assert sea.all() and (targets == -1).all() and (filled == 50).all()
