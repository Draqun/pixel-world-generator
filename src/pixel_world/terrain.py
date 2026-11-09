"""Terrain heightmap: noise shaped into an island, quantised to 16 bit."""

import numpy as np
from numpy.typing import NDArray

from pixel_world.island import island_mask
from pixel_world.noise import fbm
from pixel_world.params import Params


def generate_terrain(params: Params) -> NDArray[np.uint16]:
    """Heightmap in [0, 65535]. Erosion is applied in a later step (not yet)."""
    noise = fbm(params.seed, params.size, params.octaves)
    noise = (noise - noise.min()) / (noise.max() - noise.min())
    height = noise * island_mask(
        params.seed, params.size, params.island_exponent, params.island_warp
    )
    height = (height - height.min()) / (height.max() - height.min())
    return np.round(height * 65535).astype(np.uint16)
