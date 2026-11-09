import numpy as np
import pytest

from pixel_world.params import Params
from pixel_world.terrain import generate_terrain


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
