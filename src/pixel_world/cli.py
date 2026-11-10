"""Command line: `python -m pixel_world generate --seed N`."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from pixel_world.params import Params
from pixel_world.terrain import generate_terrain
from pixel_world.water import accumulation, drainage, rivers
from pixel_world.writer import write_world


def generate(params: Params, out: Path) -> None:
    height = generate_terrain(params)
    sea, lake, _, targets = drainage(
        height, params.sea_level, params.height_range_m, params.min_lake_depth_m
    )
    _, water = rivers(
        accumulation(targets), sea, lake, params.river_threshold, params.max_river_width
    )
    write_world(out, height, water, params)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pixel_world")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="generate a terrain heightmap")
    gen.add_argument("--seed", type=int, required=True)
    gen.add_argument("--size", type=int, default=Params.size)
    gen.add_argument("--octaves", type=int, default=Params.octaves)
    gen.add_argument("--erosion-iterations", type=int, default=Params.erosion_iterations)
    gen.add_argument("--height-range", type=float, default=Params.height_range_m)
    gen.add_argument("--sea-level", type=float, default=Params.sea_level)
    gen.add_argument("--min-lake-depth", type=float, default=Params.min_lake_depth_m)
    gen.add_argument("--river-threshold", type=int, default=Params.river_threshold)
    gen.add_argument("--max-river-width", type=int, default=Params.max_river_width)
    gen.add_argument("--out", type=Path, default=Path("out"))
    args = parser.parse_args(argv)
    try:
        params = Params(
            seed=args.seed,
            size=args.size,
            octaves=args.octaves,
            erosion_iterations=args.erosion_iterations,
            height_range_m=args.height_range,
            sea_level=args.sea_level,
            min_lake_depth_m=args.min_lake_depth,
            river_threshold=args.river_threshold,
            max_river_width=args.max_river_width,
        )
    except ValueError as error:
        parser.error(str(error))  # exits with status 2 before any file is written
    generate(params, args.out)
    print(f"wrote {args.out}/ (seed {params.seed}, {params.size}x{params.size})")
    return 0
