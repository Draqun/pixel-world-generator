"""Serialize generated map layers and metadata."""

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from pixel_world import __version__
from pixel_world.params import Params
from pixel_world.png import write_png8, write_png16


def write_world(
    out: Path, height: NDArray[np.uint16], water: NDArray[np.uint8], params: Params
) -> None:
    """Write aligned terrain and water layers with their generation parameters."""
    preview = ((height.astype(np.uint32) + 128) // 257).astype(np.uint8)
    fields = params.to_dict()
    meta = {
        "generator_version": __version__,
        "seed": fields.pop("seed"),
        "params": fields,
        "sea_level_m": params.sea_level * params.height_range_m,
        "layers": {"water.png": {"0": "dry", "1": "sea", "2": "lake", "3": "river"}},
    }
    out.mkdir(parents=True, exist_ok=True)
    write_png16(out / "heightmap.png", height)
    (out / "heightmap.r16").write_bytes(height.astype("<u2").tobytes())
    write_png8(out / "preview.png", preview)
    write_png8(out / "water.png", water)
    (out / "metadata.json").write_text(
        json.dumps(meta, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
