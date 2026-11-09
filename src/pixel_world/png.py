"""Minimal grayscale PNG writer and reader (16-bit and 8-bit).

Fixed compression level and no ancillary chunks keep the bytes reproducible.
"""

import struct
import zlib
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_GRAY = 0


def _chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def encode_png(pixels: NDArray[np.uint8] | NDArray[np.uint16]) -> bytes:
    """Encode a 2D uint8 or uint16 array as a grayscale PNG."""
    if pixels.ndim != 2 or pixels.dtype not in (np.uint8, np.uint16):
        raise ValueError("pixels must be a 2D uint8 or uint16 array")
    height, width = pixels.shape
    depth = pixels.dtype.itemsize * 8
    raw = np.ascontiguousarray(pixels.astype(f">u{pixels.dtype.itemsize}")).view(np.uint8)
    rows = np.zeros((height, 1 + raw.shape[1]), dtype=np.uint8)  # filter byte 0 per row
    rows[:, 1:] = raw.reshape(height, -1)
    ihdr = struct.pack(">IIBBBBB", width, height, depth, _GRAY, 0, 0, 0)
    return (
        _SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(rows.tobytes(), 9))
        + _chunk(b"IEND", b"")
    )


def write_png16(path: Path, pixels: NDArray[np.uint16]) -> None:
    if pixels.dtype != np.uint16:
        raise ValueError("write_png16 needs a uint16 array")
    Path(path).write_bytes(encode_png(pixels))


def write_png8(path: Path, pixels: NDArray[np.uint8]) -> None:
    if pixels.dtype != np.uint8:
        raise ValueError("write_png8 needs a uint8 array")
    Path(path).write_bytes(encode_png(pixels))


def read_png(path: Path) -> tuple[NDArray[np.uint8] | NDArray[np.uint16], int, int]:
    """Read a PNG written by this module: returns (pixels, bit_depth, colour_type)."""
    data = Path(path).read_bytes()
    if data[:8] != _SIGNATURE:
        raise ValueError("not a PNG file")
    pos, idat, header = 8, b"", None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind, body = data[pos + 4 : pos + 8], data[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    if header is None:
        raise ValueError("missing IHDR")
    width, height, depth, colour, _, _, _ = header
    if colour != _GRAY or depth not in (8, 16):
        raise ValueError("only 8/16-bit grayscale is supported")
    rows = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(height, -1)
    if (rows[:, 0] != 0).any():
        raise ValueError("only filter type 0 is supported")
    samples = np.ascontiguousarray(rows[:, 1:])
    if depth == 16:
        return samples.view(">u2").reshape(height, width).astype(np.uint16), depth, colour
    return samples.reshape(height, width).copy(), depth, colour
