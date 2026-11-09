import numpy as np

from pixel_world.noise import fbm


def block_mean(a: np.ndarray, block: int) -> np.ndarray:
    n = a.shape[0] // block
    return a.reshape(n, block, n, block).mean(axis=(1, 3))


def test_deterministic() -> None:
    assert np.array_equal(fbm(7, 64, 4), fbm(7, 64, 4))


def test_seeds_differ() -> None:
    assert not np.array_equal(fbm(1, 64, 4), fbm(2, 64, 4))


def test_finite_and_bounded() -> None:
    a = fbm(3, 128, 6)
    assert np.isfinite(a).all()
    assert a.min() >= -1.5 and a.max() <= 1.5
    assert a.std() > 0.05  # not flat


def test_more_octaves_keep_large_scale_shape() -> None:
    low = block_mean(fbm(5, 256, 4), 32)
    high = block_mean(fbm(5, 256, 6), 32)
    assert np.corrcoef(low.ravel(), high.ravel())[0, 1] > 0.99


def test_large_scale_shape_independent_of_size() -> None:
    small = block_mean(fbm(5, 128, 4), 16)
    big = block_mean(fbm(5, 256, 4), 32)
    assert np.corrcoef(small.ravel(), big.ravel())[0, 1] > 0.99
