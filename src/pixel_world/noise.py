"""Fractal gradient (Perlin-style) noise, vectorised."""

import numpy as np
from numpy.typing import NDArray

from pixel_world.seeds import step_rng

BASE_CELLS = 4  # lattice cells across the map in the first octave, independent of size


def _fade(t: NDArray[np.float64]) -> NDArray[np.float64]:
    return t * t * t * (t * (t * 6 - 15) + 10)


def _gradient_noise(rng: np.random.Generator, size: int, cells: int) -> NDArray[np.float64]:
    angles = rng.random((cells + 1, cells + 1)) * (2 * np.pi)
    gx, gy = np.cos(angles), np.sin(angles)
    u = (np.arange(size) + 0.5) / size * cells
    i = np.minimum(np.floor(u).astype(np.intp), cells - 1)
    f = u - i
    ix, iy = i[None, :], i[:, None]
    fx, fy = f[None, :], f[:, None]

    def corner(dy: int, dx: int) -> NDArray[np.float64]:
        return gx[iy + dy, ix + dx] * (fx - dx) + gy[iy + dy, ix + dx] * (fy - dy)

    sx, sy = _fade(fx), _fade(fy)
    top = corner(0, 0) * (1 - sx) + corner(0, 1) * sx
    bottom = corner(1, 0) * (1 - sx) + corner(1, 1) * sx
    return top * (1 - sy) + bottom * sy


def fbm(seed: int, size: int, octaves: int, step: str = "noise") -> NDArray[np.float64]:
    """Fractal noise in about [-1, 1], shape (size, size).

    Each octave has its own random stream, so more octaves only add detail.
    """
    total = np.zeros((size, size))
    amplitude, norm = 1.0, 0.0
    for octave in range(octaves):
        rng = step_rng(seed, f"{step}.octave{octave}")
        total += amplitude * _gradient_noise(rng, size, BASE_CELLS * 2**octave)
        norm += amplitude
        amplitude *= 0.5
    return total / norm
