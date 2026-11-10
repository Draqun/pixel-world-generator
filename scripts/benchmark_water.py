"""Measure terrain and water generation, optionally saving a diagnostic preview."""

import argparse
import resource
import time
from pathlib import Path

import numpy as np

from pixel_world.params import Params
from pixel_world.png import write_png8
from pixel_world.terrain import generate_terrain
from pixel_world.water import accumulation, drainage, rivers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("size", type=int)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    params = Params(seed=42, size=args.size)
    start = time.perf_counter()
    height = generate_terrain(params)
    terrain_time = time.perf_counter() - start
    start = time.perf_counter()
    sea, lake, _, targets = drainage(
        height, params.sea_level, params.height_range_m, params.min_lake_depth_m
    )
    area = accumulation(targets)
    _, water = rivers(area, sea, lake, params.river_threshold, params.max_river_width)
    water_time = time.perf_counter() - start
    if args.preview:
        preview = (height.astype(np.uint32) * 63 // 65535).astype(np.uint8)
        preview[water == 1] = 90
        preview[water == 2] = 160
        preview[water == 3] = 255
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        write_png8(args.preview, preview)
    print(
        f"size={args.size} terrain={terrain_time:.2f}s water={water_time:.2f}s "
        f"peak_rss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.1f} MiB"
    )


if __name__ == "__main__":
    main()
