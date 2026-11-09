"""Island shape: radial falloff with a noise-warped coastline."""

import numpy as np
from numpy.typing import NDArray

from pixel_world.noise import fbm

EDGE_BAND = 0.04  # fraction of the map over which the mask is forced to 0 at the border


def island_mask(seed: int, size: int, exponent: float, warp: float) -> NDArray[np.float64]:
    """Mask in [0, 1]: 1 near the centre, exactly 0 on the outer edge pixels."""
    axis = np.arange(size) - (size - 1) / 2
    dist = np.hypot(axis[None, :], axis[:, None]) / (size / 2)
    dist = np.maximum(dist + warp * fbm(seed, size, 2, step="island"), 0.0)
    mask = np.clip(1.0 - dist**exponent, 0.0, 1.0)
    edge = np.minimum(np.arange(size), np.arange(size)[::-1])
    to_edge = np.minimum(edge[None, :], edge[:, None]) / (EDGE_BAND * size)
    return mask * np.clip(to_edge, 0.0, 1.0)
