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
    links = []
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
            links.append(
                f"| {path.name} | [{path.name}]({path.name}/README.md) | "
                f"[Overview]({path.name}/overview/heightmap.png) |"
            )
            sea = height <= round(65535 * 0.2)
            assert sea.any() and (~sea).any(), "reference must show both land and sea"
            preview = np.where(sea, 25, 80 + 160 * (height / 65535 - 0.2) / 0.8).astype(np.uint8)
            row.append(preview)
        panels.append(np.hstack((row[0], np.full((128, 4), 255, dtype=np.uint8), row[1])))
    write_png8(out / "reference.png", np.vstack(panels))
    (out / "README.md").write_text(
        """# Overview reference suite

Eight seed-42 projects compare four geography choices on flat and spherical worlds.
Names are `<geometry>-<geography>`: flat worlds span 16000000 × 16000000 m;
spheres have radius 6000000 m. Each project guide explains its saved definition.

| Fixture | Project guide | Height image |
| --- | --- | --- |
"""
        + "\n".join(links)
        + """

## Comparison image

[reference.png](reference.png) has four rows, from top to bottom: region, island,
peninsula, continent. Columns are flat (left) and sphere (right), separated by a
white strip. Each panel has 128 rows; grayscale uses the same fixed scale:
values at or below sea datum (20% of the encoded range) are shade 25, land is
80 + 160 * (normalized height - 0.2) / 0.8, converted to uint8. This is a display
comparison, not authoritative 16-bit data or a water mask. The spherical column
uses equirectangular projection; pixel spacing varies with latitude.

## Checks and interpretation

The script asserts each fixture contains samples above and at/below sea datum.
Shape, coastline plausibility and useful visual variety require visual judgment;
those assertions do not prove realistic geography or hydrology. The project
metadata records sampling, vertical decoding and omitted layers. No regional
images, water network or timing file are produced by this suite. Runtime printed
to the terminal is machine-specific and is not deterministic output.
""",
        encoding="utf-8",
    )
    print(f"Wrote {out}/reference.png and 8 projects in {time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
