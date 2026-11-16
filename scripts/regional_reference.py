"""Generate regional fixtures and check assembled tiles, with measured process resource use."""

import resource
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from pixel_world.overview import generate_overview
from pixel_world.png import read_png
from pixel_world.regional import Region, generate_region, region_context
from pixel_world.world import WorldDefinition, canonical_json
from pixel_world.writer import create_project, write_overview, write_region


def main(out: Path) -> None:
    """Write six new reference projects; assert partition identity, including eroded terrain."""
    out.mkdir(parents=True)
    measurements = []
    for name, dimensions in (
        ("flat-small", dict(geometry="flat", width_m=16000, height_m=16000)),
        ("flat-large", dict(geometry="flat", width_m=16000000, height_m=16000000)),
        ("sphere-seam", dict(geometry="sphere", radius_m=6000000)),
    ):
        for iterations in (0, 4):
            size = 1024 if iterations == 0 else 512
            world = WorldDefinition(
                seed=42,
                geography="region",
                extent="region",
                overview_resolution=32,
                parameters=(("erosion_iterations", iterations),),
                **dimensions,
            )
            if world.geometry == "flat":
                region = Region(int(world.width_m * 0.4), int(world.height_m * 0.4), size, size)
            else:
                region = Region(-size // 2, -size // 2, size, size, anchor_lon=45, anchor_lat=0)
            path = out / f"{name}-erosion-{iterations}"
            create_project(path, world)
            start = time.perf_counter()
            directory = write_region(path, world, region)
            elapsed = time.perf_counter() - start
            peak_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            pixels, depth, _ = read_png(directory / "heightmap.png")
            assert depth == 16
            left = generate_region(world, replace(region, width=size // 2))
            right = generate_region(
                world, replace(region, x_m=region.x_m + size // 2, width=size // 2)
            )
            assert np.array_equal(pixels, np.hstack((left, right))), "partition seam"
            raw = np.fromfile(directory / "heightmap.r16", dtype="<u2").reshape(pixels.shape)
            assert np.array_equal(raw, pixels), "R16 and PNG disagree"
            write_overview(path, world, generate_overview(world))
            halo, scale_error = region_context(world, region)
            measurements.append(
                dict(
                    project=path.name,
                    size=size,
                    iterations=iterations,
                    halo_cells=halo,
                    elapsed_seconds=round(elapsed, 3),
                    cumulative_process_peak_mib=round(peak_mib, 1),
                    scale_error=scale_error,
                    artifact_bytes=sum(p.stat().st_size for p in directory.iterdir()),
                )
            )
            print(f"{path.name}: {elapsed:.3f}s, process peak {peak_mib:.1f} MiB; tiles match")
    (out / "measurements.json").write_bytes(canonical_json(measurements))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
