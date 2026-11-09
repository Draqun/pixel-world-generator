import numpy as np
import pytest

from pixel_world.params import Params
from pixel_world.terrain import base_height, generate_terrain


@pytest.fixture(scope="module", params=[1, 42, 12345])
def height(request: pytest.FixtureRequest) -> np.ndarray:
    return generate_terrain(Params(seed=request.param, size=128))


def test_dtype_shape_range(height: np.ndarray) -> None:
    assert height.dtype == np.uint16 and height.shape == (128, 128)
    assert height.min() == 0 and height.max() == 65535


def test_edge_is_low(height: np.ndarray) -> None:
    edge = np.concatenate([height[0], height[-1], height[:, 0], height[:, -1]])
    assert edge.max() <= 0.01 * 65535


def test_interior_higher_than_outer_band(height: np.ndarray) -> None:
    n = height.shape[0]
    centre = height[n // 4 : 3 * n // 4, n // 4 : 3 * n // 4].mean()
    band = n // 10
    mask = np.ones_like(height, dtype=bool)
    mask[band:-band, band:-band] = False
    assert centre > height[mask].mean()


def test_zero_iterations_is_noise_terrain() -> None:
    p = Params(seed=42, size=128, erosion_iterations=0)
    base = base_height(p)
    expected = np.round((base - base.min()) / (base.max() - base.min()) * 65535).astype(np.uint16)
    assert np.array_equal(generate_terrain(p), expected)


@pytest.fixture(scope="module", params=[1, 42])
def eroded(request: pytest.FixtureRequest) -> np.ndarray:
    return generate_terrain(Params(seed=request.param, size=128, erosion_iterations=20))


def test_erosion_changes_terrain_and_keeps_range(eroded: np.ndarray) -> None:
    plain = generate_terrain(Params(seed=1, size=128, erosion_iterations=0))
    assert eroded.min() == 0 and eroded.max() == 65535
    assert not np.array_equal(
        plain, generate_terrain(Params(seed=1, size=128, erosion_iterations=20))
    )


def test_erosion_keeps_edge_low_and_interior_high(eroded: np.ndarray) -> None:
    edge = np.concatenate([eroded[0], eroded[-1], eroded[:, 0], eroded[:, -1]])
    assert edge.max() <= 0.01 * 65535
    test_interior_higher_than_outer_band(eroded)


def test_erosion_parameters_leave_base_height_unchanged() -> None:
    a = base_height(Params(seed=3, size=64, erosion_iterations=5))
    b = base_height(Params(seed=3, size=64, erosion_iterations=90, erosion_strength=0.3))
    assert np.array_equal(a, b)
