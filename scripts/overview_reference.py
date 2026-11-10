"""Generate seed-42 geography fixtures and a fixed-scale grayscale comparison."""

import sys
import time
from pathlib import Path

import numpy as np

from pixel_world.overview import generate_overview
from pixel_world.png import write_png8
from pixel_world.world import WorldDefinition
from pixel_world.writer import create_project, write_overview


def main(out: Path) -> None:
    """Write new fixture projects; rows are region, island, peninsula, continent."""
    out.mkdir(parents=True)
    panels = []
    start = time.perf_counter()
    for geography in ("region", "island", "peninsula", "continent"):
        row = []
        for geometry in ("flat", "sphere"):
            dimensions = (
                {"width_m": 16000000, "height_m": 16000000}
                if geometry == "flat"
                else {"radius_m": 6000000}
            )
            world = WorldDefinition(
                seed=42,
                geometry=geometry,
                geography=geography,
                extent="region",
                overview_resolution=128,
                **dimensions,
            )
            path = out / f"{geometry}-{geography}"
            create_project(path, world)
            height = generate_overview(world)
            write_overview(path, world, height)
            sea = height <= round(65535 * 0.2)
            assert sea.any() and (~sea).any(), "reference must show both land and sea"
            preview = np.where(sea, 25, 80 + 160 * (height / 65535 - 0.2) / 0.8).astype(np.uint8)
            row.append(preview)
        panels.append(np.hstack((row[0], np.full((128, 4), 255, dtype=np.uint8), row[1])))
    write_png8(out / "reference.png", np.vstack(panels))
    print(f"Wrote {out}/reference.png and 8 projects in {time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
