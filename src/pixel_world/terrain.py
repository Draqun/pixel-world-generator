"""Terrain heightmap: noise shaped into an island, eroded, quantised to 16 bit."""

import numpy as np
from numpy.typing import NDArray

from pixel_world.erosion import erode
from pixel_world.island import island_mask
from pixel_world.noise import fbm
from pixel_world.params import Params


def _unit(a: NDArray[np.float64]) -> NDArray[np.float64]:
    return (a - a.min()) / (a.max() - a.min())


def base_height(params: Params) -> NDArray[np.float64]:
    """Island-shaped noise in [0, 1] before erosion; independent of the erosion parameters."""
    noise = _unit(fbm(params.seed, params.size, params.octaves))
    return noise * island_mask(params.seed, params.size, params.island_exponent, params.island_warp)


def generate_terrain(params: Params) -> NDArray[np.uint16]:
    """Heightmap in [0, 65535]."""
    height = erode(
        base_height(params),
        params.erosion_iterations,
        params.erosion_strength,
        params.erosion_talus,
    )
    return np.round(_unit(height) * 65535).astype(np.uint16)
