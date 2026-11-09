"""Command line: `python -m pixel_world generate --seed N`."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from pixel_world import __version__
from pixel_world.params import Params
from pixel_world.png import write_png8, write_png16
from pixel_world.terrain import generate_terrain


def _metadata(params: Params) -> str:
    fields = params.to_dict()
    meta = {"generator_version": __version__, "seed": fields.pop("seed"), "params": fields}
    return json.dumps(meta, sort_keys=True, indent=2) + "\n"


def generate(params: Params, out: Path) -> None:
    height = generate_terrain(params)
    preview = ((height.astype(np.uint32) + 128) // 257).astype(np.uint8)  # round(h / 257)
    out.mkdir(parents=True, exist_ok=True)
    write_png16(out / "heightmap.png", height)
    write_png8(out / "preview.png", preview)
    (out / "metadata.json").write_text(_metadata(params), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pixel_world")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="generate a terrain heightmap")
    gen.add_argument("--seed", type=int, required=True)
    gen.add_argument("--size", type=int, default=Params.size)
    gen.add_argument("--octaves", type=int, default=Params.octaves)
    gen.add_argument("--erosion-iterations", type=int, default=Params.erosion_iterations)
    gen.add_argument("--out", type=Path, default=Path("out"))
    args = parser.parse_args(argv)
    try:
        params = Params(
            seed=args.seed,
            size=args.size,
            octaves=args.octaves,
            erosion_iterations=args.erosion_iterations,
        )
    except ValueError as error:
        parser.error(str(error))  # exits with status 2 before any file is written
    generate(params, args.out)
    print(f"wrote {args.out}/ (seed {params.seed}, {params.size}x{params.size})")
    return 0
