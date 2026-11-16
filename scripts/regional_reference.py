"""Generate regional fixtures and check assembled tiles, with measured process resource use."""

import json
import resource
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from pixel_world.overview import generate_overview
from pixel_world.png import read_png
from pixel_world.regional import Region, generate_region, region_context
from pixel_world.world import canonical_json
from pixel_world.writer import load_project


def _command(project: Path, name: str, *args: object) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "pixel_world", name, "--project", str(project), *map(str, args)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


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
            path = out / f"{name}-erosion-{iterations}"

            dimension_args = [
                item
                for key, value in dimensions.items()
                for item in ("--" + key.replace("_", "-"), value)
            ]
            _command(
                path,
                "world-create",
                "--seed",
                42,
                "--geography",
                "region",
                "--extent",
                "region",
                "--overview-resolution",
                32,
                "--erosion-iterations",
                iterations,
                *dimension_args,
            )
            world = load_project(path).definition
            x_px, y_px = (12.8, 12.8) if world.geometry == "flat" else (40, 16)
            selected = _command(
                path,
                "world-select",
                "--overview-x",
                x_px,
                "--overview-y",
                y_px,
                "--width",
                size,
                "--height",
                size,
            )
            region = Region(**selected["grid"])
            export_args = ["--x", region.x_m, "--y", region.y_m, "--width", size, "--height", size]
            if region.anchor_lon is not None:
                export_args += [
                    "--anchor-lon",
                    region.anchor_lon,
                    "--anchor-lat",
                    region.anchor_lat,
                ]
            start = time.perf_counter()
            directory = Path(_command(path, "region-export", *export_args)["directory"])
            elapsed = time.perf_counter() - start
            peak_mib = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
            pixels, depth, _ = read_png(directory / "heightmap.png")
            assert depth == 16
            left = generate_region(world, replace(region, width=size // 2))
            right = generate_region(
                world, replace(region, x_m=region.x_m + size // 2, width=size // 2)
            )
            assert np.array_equal(pixels, np.hstack((left, right))), "partition seam"
            raw = np.fromfile(directory / "heightmap.r16", dtype="<u2").reshape(pixels.shape)
            assert np.array_equal(raw, pixels), "R16 and PNG disagree"
            previous = (directory / "heightmap.r16").read_bytes()
            _command(path, "world-overview")
            assert np.array_equal(
                generate_overview(world), read_png(path / "overview/heightmap.png")[0]
            )
            assert (directory / "heightmap.r16").read_bytes() == previous
            assert len(_command(path, "world-info")["coverage"]) == 2
            halo, scale_error = region_context(world, region)
            measurements.append(
                dict(
                    project=path.name,
                    size=size,
                    iterations=iterations,
                    halo_cells=halo,
                    elapsed_seconds=round(elapsed, 3),
                    cumulative_child_peak_mib=round(peak_mib, 1),
                    scale_error=scale_error,
                    artifact_bytes=sum(p.stat().st_size for p in directory.iterdir()),
                )
            )
            print(f"{path.name}: {elapsed:.3f}s, child peak {peak_mib:.1f} MiB; tiles match")
    (out / "measurements.json").write_bytes(canonical_json(measurements))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
