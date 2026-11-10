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


def test_branching_catchment_accumulates_exactly() -> None:
    from pixel_world.water import accumulation

    # 0 and 2 join at 4, which drains via 7 to outlet 8.
    targets = np.array([[4, -1, 4], [-1, 7, -1], [-1, 8, -1]], dtype=np.int64)
    area = accumulation(targets)
    assert area.tolist() == [[1, 1, 1], [1, 3, 1], [1, 4, 5]]


def test_rivers_are_connected_and_preserve_water_categories() -> None:
    from pixel_world.water import accumulation, rivers

    ground = np.full((9, 9), 10, dtype=np.uint16)
    ground[0, 4] = 0
    sea, lake, filled, targets = drainage(ground, 0.0, 1000, 1)
    area = accumulation(targets)
    centre, water = rivers(area, sea, lake, 3, 5)
    assert centre.any()
    for i in np.flatnonzero(centre):
        while targets.flat[i] != -1 and not sea.flat[i] and not lake.flat[i]:
            next_i = targets.flat[i]
            assert filled.flat[next_i] <= filled.flat[i]
            assert centre.flat[next_i] or sea.flat[next_i] or lake.flat[next_i]
            i = next_i
    assert np.all(water[sea] == 1)
    assert np.all(water[lake] == 2)
    assert not rivers(area, sea, lake, 1000, 5)[0].any()


def test_wider_channels_and_category_precedence() -> None:
    from pixel_world.water import rivers

    area = np.zeros((11, 15), dtype=np.int64)
    area[5, 3], area[5, 11] = 4, 64
    sea = np.zeros_like(area, dtype=bool)
    lake = sea.copy()
    sea[5, 11], lake[5, 10] = True, True
    _, water = rivers(area, sea, lake, 4, 5)
    assert water[5, 11] == 1 and water[5, 10] == 2
    assert water[3, 11] == 3 and water[3, 3] == 0


def test_long_drainage_chain_counts_every_cell() -> None:
    from pixel_world.water import accumulation

    targets = np.arange(1, 101, dtype=np.int64).reshape(1, 100)
    targets[0, -1] = -1
    assert accumulation(targets)[0, -1] == 100
