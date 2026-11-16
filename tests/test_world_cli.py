import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from pixel_world.cli import main
from pixel_world.coordinates import local_to_lonlat
from pixel_world.overview import generate_overview, overview_scale, overview_to_world
from pixel_world.png import read_png
from pixel_world.regional import Region, generate_region
from pixel_world.world import WorldDefinition
from pixel_world.writer import create_project, load_project, write_region


def command(capsys, name, path, *args):
    assert main([name, "--project", str(path), *map(str, args)]) == 0
    return json.loads(capsys.readouterr().out)


def create(capsys, path, geometry="flat", seed=42, **kwargs):
    args = [
        "--seed",
        seed,
        "--geometry",
        geometry,
        "--geography",
        "region",
        "--overview-resolution",
        16,
        "--erosion-iterations",
        2,
    ]
    args += (
        ["--width-m", 16000000, "--height-m", 16000000]
        if geometry == "flat"
        else ["--radius-m", 6000000]
    )
    for key, value in kwargs.items():
        args += ["--" + key.replace("_", "-"), value]
    return command(capsys, "world-create", path, *args)


def hashes(path):
    return {
        str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in path.rglob("*")
        if p.is_file()
    }


def export(capsys, path, grid):
    args = [
        "--x",
        grid["x_m"],
        "--y",
        grid["y_m"],
        "--width",
        grid["width"],
        "--height",
        grid["height"],
    ]
    if grid["anchor_lon"] is not None:
        args += ["--anchor-lon", grid["anchor_lon"], "--anchor-lat", grid["anchor_lat"]]
    return command(capsys, "region-export", path, *args)


@pytest.mark.parametrize("geometry", ["flat", "sphere"])
def test_create_select_export_and_resume(capsys, tmp_path, geometry):
    path = tmp_path / "new project"
    created = create(capsys, path, geometry)
    world = load_project(path).definition
    assert created["world_id"] == world.world_id
    assert not (path / "overview").exists()
    selected = command(
        capsys,
        "world-select",
        path,
        "--overview-x",
        8.5,
        "--overview-y",
        8.5,
        "--width",
        24,
        "--height",
        16,
    )
    position = overview_to_world(world, 8.5, 8.5)
    assert selected["position"] == pytest.approx(position)
    assert selected["pixel_span_m"] == pytest.approx(overview_scale(world, *position))
    grid = selected["grid"]
    if geometry == "flat":
        assert grid["x_m"] + 12 == position[0]
        assert grid["y_m"] + 8 == position[1]
    else:
        assert (grid["anchor_lon"], grid["anchor_lat"]) == pytest.approx(position)
        assert (grid["x_m"], grid["y_m"]) == (-12, -8)
    first = export(capsys, path, grid)
    before = hashes(path / "regions")
    command(capsys, "world-overview", path)
    assert hashes(path / "regions") == before
    info = command(capsys, "world-info", path)
    assert info["definition"] == world.to_dict() | {
        "parameters": [list(p) for p in world.parameters]
    }
    assert len(info["coverage"]) == 2
    neighbour = grid | {"x_m": grid["x_m"] + grid["width"]}
    second = export(capsys, path, neighbour)
    assert first["directory"] != second["directory"]
    assert all(hashes(path / "regions")[name] == digest for name, digest in before.items())
    assert len(command(capsys, "world-info", path)["coverage"]) == 3
    for metadata_path in [
        path / "overview/metadata.json",
        Path(first["directory"]) / "metadata.json",
    ]:
        metadata = json.loads(metadata_path.read_text())
        assert metadata["water"] == {
            "status": "omitted",
            "coverage": None,
            "resolution_m": None,
            "exact_global_drainage": False,
        }
        assert "water" in metadata["omitted_layers"]
        assert not (metadata_path.parent / "water.png").exists()


@pytest.mark.parametrize("geometry", ["flat", "sphere"])
def test_spherical_selection_reuses_anchor_and_flat_selection_snaps(capsys, tmp_path, geometry):
    path = tmp_path / "project"
    create(capsys, path, geometry)
    world = load_project(path).definition
    args = ["--overview-x", 8.50001, "--overview-y", 8.5, "--width", 16, "--height", 16]
    position = overview_to_world(world, 8.50001, 8.5)
    if geometry == "sphere":
        anchor = overview_to_world(world, 8.5, 8.5)
        args += ["--anchor-lon", anchor[0], "--anchor-lat", anchor[1]]
    selection = command(capsys, "world-select", path, *args)
    grid = selection["grid"]
    if geometry == "sphere":
        assert (grid["anchor_lon"], grid["anchor_lat"]) == pytest.approx(anchor)
        centre = local_to_lonlat(*anchor, grid["x_m"] + 8, grid["y_m"] + 8, world.radius_m)
        assert centre == pytest.approx(position, abs=1e-5)
    else:
        assert 0 <= position[0] - (grid["x_m"] + 8) < 1


@pytest.mark.parametrize("geometry", ["flat", "sphere"])
@pytest.mark.parametrize("seed", [42, 43])
def test_end_to_end_order_cache_independence_and_partition_hashes(capsys, tmp_path, geometry, seed):
    for name, reverse in (("a", False), ("b", True)):
        path = tmp_path / name
        create(capsys, path, geometry, seed, extent="region")
        if not reverse:
            command(capsys, "world-overview", path)
        selected = command(
            capsys,
            "world-select",
            path,
            "--overview-x",
            8.5,
            "--overview-y",
            8.5,
            "--width",
            16,
            "--height",
            16,
        )
        a = selected["grid"]
        b = a | {"x_m": a["x_m"] + 16}
        directories = {}
        for grid in (b, a) if reverse else (a, b):
            result = export(capsys, path, grid)
            directories[grid["x_m"]] = Path(result["directory"])
        if reverse:
            command(capsys, "world-overview", path)
        world = load_project(path).definition
        combined = generate_region(world, Region(**(a | {"width": 32})))
        tiles = []
        for grid in (a, b):
            pixels, _, _ = read_png(directories[grid["x_m"]] / "heightmap.png")
            tiles.append(pixels)
        assert np.array_equal(combined, np.hstack(tiles))
        assert np.array_equal(
            generate_overview(world), read_png(path / "overview/heightmap.png")[0]
        )
    assert hashes(tmp_path / "a") == hashes(tmp_path / "b")


@pytest.mark.parametrize(
    "args",
    [
        [
            "--seed",
            "-1",
            "--geometry",
            "flat",
            "--geography",
            "region",
            "--width-m",
            "100",
            "--height-m",
            "100",
        ],
        ["--seed", "42", "--geometry", "sphere", "--geography", "region", "--radius-m", "nan"],
        ["--seed", "42", "--geometry", "flat", "--geography", "region", "--width-m", "100"],
        [
            "--seed",
            "42",
            "--geometry",
            "flat",
            "--geography",
            "region",
            "--width-m",
            "100",
            "--height-m",
            "100",
            "--erosion-iterations",
            "65",
        ],
    ],
)
def test_create_invalid_input_writes_nothing(capsys, tmp_path, args):
    path = tmp_path / "missing"
    with pytest.raises(SystemExit):
        main(["world-create", "--project", str(path), *args])
    assert not path.exists()


@pytest.mark.parametrize(
    "args",
    [
        ["--x", "-1", "--y", "0", "--width", "16", "--height", "16"],
        ["--x", "0", "--y", "0", "--width", "2048", "--height", "2048"],
        ["--x", "0", "--y", "0", "--width", "16", "--height", "16", "--water", "exact"],
        ["--x", "0", "--y", "0", "--width", "16", "--height", "16", "--water", "coarse"],
        ["--x", "0", "--y", "0", "--width", "16", "--height", "16", "--seed", "43"],
    ],
)
def test_export_rejections_preserve_project(capsys, tmp_path, args):
    path = tmp_path / "project"
    create(capsys, path)
    before = hashes(path)
    with pytest.raises(SystemExit):
        main(["region-export", "--project", str(path), *args])
    assert hashes(path) == before


@pytest.mark.parametrize("water", ["exact", "coarse", "unknown"])
def test_python_water_requests_fail_before_generation(tmp_path, monkeypatch, water):
    import pixel_world.writer as writer

    world = WorldDefinition(seed=42, geometry="flat", geography="region", width_m=100, height_m=100)
    create_project(tmp_path / "project", world)
    before = hashes(tmp_path)
    monkeypatch.setattr(
        writer, "generate_region", lambda *args: pytest.fail("must reject before sampling")
    )
    with pytest.raises(ValueError, match="water.*unavailable"):
        write_region(tmp_path / "project", world, Region(0, 0, 16, 16), water=water)
    assert hashes(tmp_path) == before


def test_world_help_lists_commands(capsys):
    assert main(["--help"]) == 0
    text = capsys.readouterr().out
    for name in ("world-create", "world-info", "world-overview", "world-select", "region-export"):
        assert name in text


@pytest.mark.parametrize("geometry", ["flat", "sphere"])
def test_make_workflow_in_fresh_processes(tmp_path, geometry):
    path = tmp_path / "world with spaces"
    dimensions = (
        "--width-m 16000000 --height-m 16000000" if geometry == "flat" else "--radius-m 6000000"
    )

    def make(target, args=""):
        result = subprocess.run(
            ["make", "--no-print-directory", "-s", target, f"PROJECT={path}", f"ARGS={args}"],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    make(
        "world-create",
        f"--seed 42 --geometry {geometry} --geography region --overview-resolution 16 {dimensions}",
    )
    selected = make("world-select", "--overview-x 8.5 --overview-y 8.5 --width 16 --height 16")
    grid = selected["grid"]
    anchor = (
        ""
        if geometry == "flat"
        else f"--anchor-lon {grid['anchor_lon']} --anchor-lat {grid['anchor_lat']}"
    )
    make("region-export", f"--x {grid['x_m']} --y {grid['y_m']} --width 16 --height 16 {anchor}")
    make("world-overview")
    assert len(make("world-info")["coverage"]) == 2


@pytest.mark.parametrize("geometry", ["flat", "sphere"])
def test_world_artifact_golden(capsys, tmp_path, geometry):
    create(capsys, tmp_path / "world", geometry)
    selection = command(
        capsys,
        "world-select",
        tmp_path / "world",
        "--overview-x",
        8.5,
        "--overview-y",
        8.5,
        "--width",
        16,
        "--height",
        16,
    )
    export(capsys, tmp_path / "world", selection["grid"])
    command(capsys, "world-overview", tmp_path / "world")
    digest = hashlib.sha256()
    for name, file_hash in sorted(hashes(tmp_path / "world").items()):
        digest.update(name.encode() + file_hash.encode())
    # Includes definition, coverage, overview and PNG/R16/metadata for the eroded region.
    # Update deliberately with the generator version when the artifact contract changes.
    assert (
        digest.hexdigest()
        == {
            "flat": "b564dd20aa4b93a0214f212091e334865fbd9f781cf4a1586a6c8ce4e84bbfce",
            "sphere": "be393deb14cec54846c4b002ab01289091255626e69daab35adf077189a40c14",
        }[geometry]
    )


@pytest.mark.parametrize("geometry,resolution", [("flat", 8192), ("sphere", 1024)])
def test_create_rejects_unusable_overview_lattice_before_writes(
    capsys, tmp_path, geometry, resolution
):
    with pytest.raises(SystemExit):
        create(capsys, tmp_path / "world", geometry, overview_resolution=resolution)
    assert not (tmp_path / "world").exists()
