import pytest

from pixel_world.params import Params


def test_defaults() -> None:
    p = Params(seed=1)
    assert p.size == 1024
    assert p.to_dict() == {
        "seed": 1,
        "size": 1024,
        "octaves": 6,
        "erosion_iterations": 50,
        "island_exponent": 2.5,
        "island_warp": 0.25,
        "erosion_strength": 0.04,
        "erosion_talus": 0.004,
        "height_range_m": 400.0,
        "sea_level": 0.2,
        "min_lake_depth_m": 1.0,
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"seed": -1},
        {"seed": "abc"},
        {"seed": 1.5},
        {"seed": True},
        {"seed": 1, "size": 63},
        {"seed": 1, "size": 8193},
        {"seed": 1, "size": 100.0},
        {"seed": 1, "octaves": 0},
        {"seed": 1, "erosion_iterations": -1},
        {"seed": 1, "island_exponent": 0},
        {"seed": 1, "island_warp": -0.1},
        {"seed": 1, "island_warp": "x"},
        {"seed": 1, "erosion_strength": -1},
        {"seed": 1, "erosion_talus": 0},
        {"seed": 1, "height_range_m": 0},
        {"seed": 1, "height_range_m": -5},
    ],
)
def test_rejects_invalid(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        Params(**kwargs)


@pytest.mark.parametrize("size", [64, 8192])
def test_size_bounds_accepted(size: int) -> None:
    assert Params(seed=0, size=size).size == size


@pytest.mark.parametrize(
    "name,value",
    [
        ("sea_level", -0.1),
        ("sea_level", 1),
        ("sea_level", float("nan")),
        ("sea_level", float("inf")),
        ("min_lake_depth_m", -1),
        ("min_lake_depth_m", float("nan")),
        ("min_lake_depth_m", float("inf")),
    ],
)
def test_invalid_water_controls(name: str, value: float) -> None:
    with pytest.raises(ValueError):
        Params(seed=1, **{name: value})
