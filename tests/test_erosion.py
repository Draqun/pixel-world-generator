import numpy as np

from pixel_world.erosion import erode


def ring(a: np.ndarray) -> np.ndarray:
    m = np.ones(a.shape, dtype=bool)
    m[1:-1, 1:-1] = False
    return a[m]


def bumpy(n: int = 32) -> np.ndarray:
    rng = np.random.default_rng(0)
    y, x = np.mgrid[:n, :n] / n
    return np.clip(1 - np.hypot(x - 0.5, y - 0.5) * 2, 0, 1) + rng.random((n, n)) * 0.05


def test_zero_iterations_is_identity_copy() -> None:
    h = bumpy()
    out = erode(h, 0, 0.02, 0.01)
    assert np.array_equal(out, h) and out is not h


def test_deterministic() -> None:
    h = bumpy()
    assert np.array_equal(erode(h, 5, 0.02, 0.01), erode(h, 5, 0.02, 0.01))


def test_ring_kept_and_range_not_exceeded() -> None:
    h = bumpy()
    out = erode(h, 10, 0.05, 0.01)
    assert np.array_equal(ring(out), ring(h))
    assert out.min() >= h.min() - 1e-12 and out.max() <= h.max() + 1e-12


def test_tilted_plane_stays_monotone() -> None:
    x = np.tile(np.linspace(1, 0, 16), (16, 1))
    out = erode(x, 20, 0.05, 0.5)
    assert (np.diff(out[1:-1], axis=1) <= 1e-12).all()


def test_single_peak_is_lowered() -> None:
    h = np.zeros((33, 33))
    h[16, 16] = 1.0
    out = erode(h, 5, 0.02, 0.01)
    assert out[16, 16] < 1.0 and out.sum() > 0


def test_pit_is_not_dug_deeper() -> None:
    h = np.tile(np.linspace(1, 0.5, 16), (16, 1))
    h[8, 8] = 0.1
    out = erode(h, 30, 0.2, 0.5)
    assert out.min() >= 0.1 - 1e-12


def test_proven_halo_matches_full_rectangular_catchment() -> None:
    from pixel_world.erosion import SWEEPS

    # Strong relief and low talus exercise both accumulation and two-hop transfers.
    height = np.random.default_rng(42).random((140, 170))
    for iterations in (1, 3):
        halo = (SWEEPS + 3) * iterations + 1
        full = erode(height, iterations, 0.05, 0.001)
        local = erode(height[60 - halo : 70 + halo, 70 - halo : 90 + halo], iterations, 0.05, 0.001)
        assert np.array_equal(full[60:70, 70:90], local[halo:-halo, halo:-halo])
