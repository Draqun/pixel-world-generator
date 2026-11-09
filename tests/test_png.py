from pathlib import Path

import numpy as np
import pytest

from pixel_world.png import read_png, write_png8, write_png16


def test_roundtrip_16bit(tmp_path: Path) -> None:
    px = np.arange(12 * 7, dtype=np.uint16).reshape(12, 7) * 700
    f = tmp_path / "h.png"
    write_png16(f, px)
    out, depth, colour = read_png(f)
    assert (depth, colour) == (16, 0)
    assert out.shape == (12, 7)
    assert np.array_equal(out, px)


def test_roundtrip_8bit(tmp_path: Path) -> None:
    px = (np.arange(5 * 9) % 256).astype(np.uint8).reshape(5, 9)
    f = tmp_path / "p.png"
    write_png8(f, px)
    out, depth, colour = read_png(f)
    assert (depth, colour) == (8, 0)
    assert np.array_equal(out, px)


def test_extreme_values_survive(tmp_path: Path) -> None:
    px = np.array([[0, 65535], [256, 255]], dtype=np.uint16)
    write_png16(tmp_path / "e.png", px)
    assert np.array_equal(read_png(tmp_path / "e.png")[0], px)


def test_same_array_same_bytes(tmp_path: Path) -> None:
    px = np.random.default_rng(0).integers(0, 65536, (32, 32), dtype=np.uint16)
    write_png16(tmp_path / "a.png", px)
    write_png16(tmp_path / "b.png", px)
    assert (tmp_path / "a.png").read_bytes() == (tmp_path / "b.png").read_bytes()


def test_rejects_wrong_dtype(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_png16(tmp_path / "x.png", np.zeros((2, 2), dtype=np.uint8))
    with pytest.raises(ValueError):
        write_png8(tmp_path / "x.png", np.zeros((2, 2), dtype=np.uint16))
