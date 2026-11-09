"""Vectorised grid erosion: stream-power incision along D8 flow plus thermal relaxation.

Heights are floats where 1.0 is the full height range; slopes are per pixel.
No randomness: the result depends only on the input heights and parameters.
"""

import numpy as np
from numpy.typing import NDArray

SWEEPS = 12  # flow-accumulation relaxation sweeps: drainage area counts cells within 12 hops
AREA_EXPONENT = 0.5  # stream-power exponent on drainage area
THERMAL_RATE = 0.5  # fraction of a slope's excess moved per iteration

# Fixed order: ties between equally steep neighbours always go to the first one.
_NEIGHBOURS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def _shifted(padded: NDArray[np.float64], n: int, dy: int, dx: int) -> NDArray[np.float64]:
    return padded[1 + dy : 1 + dy + n, 1 + dx : 1 + dx + n]


def _steepest_descent(h: NDArray[np.float64]) -> tuple[NDArray[np.intp], NDArray[np.float64]]:
    """Flat index of each cell's steepest lower neighbour (itself if none) and the slope to it."""
    n = h.shape[0]
    padded = np.pad(h, 1, constant_values=np.inf)
    own = np.arange(n * n).reshape(n, n)
    target, slope = own.copy(), np.zeros_like(h)
    for dy, dx in _NEIGHBOURS:
        drop = (h - _shifted(padded, n, dy, dx)) / np.hypot(dy, dx)
        better = drop > slope
        slope = np.where(better, drop, slope)
        target = np.where(better, own + dy * n + dx, target)
    return target, slope


def _drainage_area(target: NDArray[np.intp]) -> NDArray[np.float64]:
    flat = target.ravel()
    own = np.arange(flat.size)
    area = np.ones(flat.size)
    for _ in range(SWEEPS):
        inflow = np.bincount(flat, weights=np.where(flat == own, 0.0, area), minlength=flat.size)
        area = 1.0 + inflow
    return area.reshape(target.shape)


def _incise(h: NDArray[np.float64], strength: float) -> NDArray[np.float64]:
    target, slope = _steepest_descent(h)
    area = _drainage_area(target)
    lowest = h.ravel()[target.ravel()].reshape(h.shape)
    # Never cut below the cell it drains into, so incision cannot create new pits.
    return np.maximum(h - strength * area**AREA_EXPONENT * slope, lowest)


def _relax(h: NDArray[np.float64], talus: float) -> NDArray[np.float64]:
    """Move material downhill wherever a slope is steeper than `talus` (mass is conserved)."""
    n = h.shape[0]
    padded = np.pad(h, 1, constant_values=np.inf)
    received = np.zeros((n + 2, n + 2))
    given = np.zeros_like(h)
    for dy, dx in _NEIGHBOURS:
        dist = np.hypot(dy, dx)
        excess = np.maximum(h - _shifted(padded, n, dy, dx) - talus * dist, 0.0)
        move = THERMAL_RATE * excess / len(_NEIGHBOURS)
        given += move
        _shifted(received, n, dy, dx)[...] += move
    return h - given + received[1:-1, 1:-1]


def erode(
    height: NDArray[np.float64], iterations: int, strength: float, talus: float
) -> NDArray[np.float64]:
    """Erode a square height grid. The outer ring of cells keeps its values."""
    h = height.copy()
    ring = np.ones(h.shape, dtype=bool)
    ring[1:-1, 1:-1] = False
    fixed = h[ring].copy()
    for _ in range(iterations):
        h = _relax(_incise(h, strength), talus)
        h[ring] = fixed
    return h
