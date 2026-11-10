import hashlib
import json
from dataclasses import replace

import numpy as np
import pytest

from pixel_world.overview import (
    generate_overview,
    geography_field,
    overview_shape,
    overview_to_world,
    world_to_overview,
)
from pixel_world.png import read_png
from pixel_world.seeds import step_rng
from pixel_world.world import WorldDefinition
from pixel_world.writer import create_project, load_project, write_overview


def flat(geography="region", **kwargs):
    return WorldDefinition(
        seed=42,
        geometry="flat",
        geography=geography,
        width_m=16000000,
        height_m=16000000,
        overview_resolution=64,
        **kwargs,
    )


def test_extent_is_independent_and_persisted_without_overview(tmp_path):
    a = flat("island", extent="region")
    b = replace(a, extent="world")
    create_project(tmp_path / "a", a)
    assert load_project(tmp_path / "a").definition.extent == "region"
    assert sorted(p.name for p in (tmp_path / "a").iterdir()) == ["coverage.json", "world.json"]
    assert np.array_equal(generate_overview(a), generate_overview(b))
    with pytest.raises(ValueError):
        replace(a, extent="unknown")


@pytest.mark.parametrize("geography", ["island", "peninsula", "continent", "region", "world"])
def test_flat_geography_reference(geography):
    world = flat(geography, extent="region")
    height = generate_overview(world)
    land = height > round(65535 * 0.2)
    assert land.any() and (~land).any()
    if geography == "island":
        assert not land[0].any() and not land[-1].any()
        assert not land[:, 0].any() and not land[:, -1].any()
        assert land[32, 32]
    elif geography == "peninsula":
        assert land[32, 0] and land[32, 32]
        assert not land[0, 0] and not land[-1, 0] and not land[32, -1]
        assert land[32, :32].all()
    elif geography == "continent":
        assert land[32, 0] and not land[32, -1]
    else:
        assert land[0].any() or land[-1].any() or land[:, 0].any() or land[:, -1].any()


@pytest.mark.parametrize("geography", ["region", "island", "peninsula", "continent"])
def test_sphere_is_continuous_at_seam_and_poles(geography):
    world = WorldDefinition(
        seed=42,
        geometry="sphere",
        geography=geography,
        radius_m=6000000,
        overview_resolution=32,
        extent="region",
    )
    values = geography_field(
        world,
        np.array([-180.0, 180.0, -80.0, 80.0]),
        np.array([0.0, 0.0, 90.0, 90.0]),
        step_rng(42, "world.geography"),
    )
    assert values[0] == values[1]
    assert values[2] == values[3]
    pixels = generate_overview(world)
    assert pixels.shape == (32, 64) and pixels.dtype == np.uint16


@pytest.mark.parametrize("sphere", [False, True])
def test_selection_roundtrips_and_anchor_samples(sphere):
    world = (
        WorldDefinition(
            seed=42, geometry="sphere", geography="world", radius_m=6000000, overview_resolution=32
        )
        if sphere
        else flat()
    )
    pixels = generate_overview(world)
    rows, cols = pixels.shape
    for column, row in [(0, 0), (cols // 2, rows // 2), (cols - 1, rows - 1)]:
        first, second = overview_to_world(world, column + 0.5, row + 0.5)
        assert world_to_overview(world, first, second) == pytest.approx((column + 0.5, row + 0.5))
        value = geography_field(
            world, np.array(first), np.array(second), step_rng(42, "world.geography")
        )
        assert int(np.rint(value * 65535)) == pixels[row, column]
    if not sphere:
        assert overview_to_world(world, 0.5, 0.5) == (125000, 125000)


@pytest.mark.parametrize("sphere", [False, True])
def test_export_is_deterministic_and_records_scale(tmp_path, sphere):
    world = (
        WorldDefinition(
            seed=42, geometry="sphere", geography="island", radius_m=6000000, overview_resolution=32
        )
        if sphere
        else flat("peninsula")
    )
    pixels = generate_overview(world)

    def hashes(path):
        return {
            str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*")
            if p.is_file()
        }

    for name in ("a", "b"):
        path = tmp_path / name
        create_project(path, world)
        before = (path / "world.json").read_bytes()
        write_overview(path, world, pixels)
        assert (path / "world.json").read_bytes() == before
        assert len(load_project(path).coverage) == 1
        png, depth, _ = read_png(path / "overview/heightmap.png")
        assert depth == 16 and np.array_equal(png, pixels)
    assert hashes(tmp_path / "a") == hashes(tmp_path / "b")
    meta = json.loads((tmp_path / "a/overview/metadata.json").read_text())
    assert meta["sampling"]["unresolved_detail"]
    assert meta["world_id"] == world.world_id
    assert meta["projection"]["name"] == ("equirectangular" if sphere else "flat")
    assert len(meta["reference_samples"]) == 5
    if not sphere:
        assert meta["projection"]["pixel_width_m"] == 250000
    before = hashes(tmp_path / "a")
    with pytest.raises(FileExistsError):
        write_overview(tmp_path / "a", world, pixels)
    assert hashes(tmp_path / "a") == before


def test_resolution_budget_and_invalid_selection_fail_before_writes(tmp_path):
    large = replace(flat(), overview_resolution=8192)
    with pytest.raises(ValueError, match="sample"):
        generate_overview(large)
    path = tmp_path / "world"
    create_project(path, flat())
    with pytest.raises(ValueError):
        write_overview(path, flat(), np.zeros((1, 1), dtype=np.uint16))
    assert not (path / "overview").exists()
    for position in [(-1, 0), (64, 0), (0, 64), (float("nan"), 0)]:
        with pytest.raises(ValueError):
            overview_to_world(flat(), *position)
    assert overview_shape(replace(flat(), width_m=8000000)) == (64, 32)


@pytest.mark.parametrize("geography", ["region", "island", "peninsula", "continent", "world"])
def test_wrapped_geography_joins_without_output_edge_mask(geography):
    world = flat(geography, boundary="wrap_x")
    x = np.array([-1.0, 15999999.0, 0.0, 16000000.0])
    y = np.array([8000000.0] * 4)
    heights = geography_field(world, x, y, step_rng(42, "world.geography"))
    assert heights[0] == heights[1]
    assert heights[2] == heights[3]


def test_spherical_landform_reference_positions():
    world = WorldDefinition(seed=42, geometry="sphere", geography="peninsula", radius_m=6000000)
    heights = geography_field(
        world,
        np.array([-90.0, -45.0, -5.0, 10.0, 0.0]),
        np.array([0.0, 0.0, 0.0, 0.0, 30.0]),
        step_rng(42, "world.geography"),
    )
    assert (heights[:3] > 0.2).all()  # mainland through connected equatorial tongue
    assert (heights[3:] < 0.2).all()  # water beyond the tip and beside it


def test_overview_seed_isolation_and_request_partition():
    world = flat("region")
    first = generate_overview(world)
    assert not np.array_equal(first, generate_overview(replace(world, seed=43)))
    step_rng(42, "future.biomes").random(100)
    assert np.array_equal(first, generate_overview(world))
    # Sampling a subset has no dependence on the number/order of earlier requests.
    x = np.array([1000000.0, 8000000.0, 15000000.0])
    y = np.array([3000000.0] * 3)
    all_samples = geography_field(world, x, y, step_rng(42, "world.geography"))
    for index in [2, 0, 1]:
        assert (
            geography_field(world, x[index], y[index], step_rng(42, "world.geography"))
            == all_samples[index]
        )


def test_large_extent_does_not_change_overview_allocation():
    world = flat()
    small = generate_overview(replace(world, width_m=16000, height_m=16000))
    large = generate_overview(world)
    assert small.shape == large.shape == (64, 64)
    assert small.nbytes == large.nbytes == 8192
    assert np.array_equal(small, large)


def test_failed_overview_publication_preserves_existing_files(tmp_path, monkeypatch):
    import pixel_world.writer as writer

    world = flat()
    path = tmp_path / "project"
    create_project(path, world)
    (path / "existing-region.bin").write_bytes(b"existing region")
    before = {p.name: p.read_bytes() for p in path.iterdir()}

    def fail_publish(*args):
        raise OSError("failed publication")

    monkeypatch.setattr(writer.os, "replace", fail_publish)
    with pytest.raises(OSError):
        write_overview(path, world, generate_overview(world))
    assert {p.name: p.read_bytes() for p in path.iterdir()} == before


def test_selection_scale_is_physical_and_varies_with_latitude():
    from pixel_world.overview import overview_scale

    assert overview_scale(flat(), 8000000, 8000000) == (250000, 250000)
    sphere = WorldDefinition(
        seed=42, geometry="sphere", geography="world", radius_m=6000000, overview_resolution=32
    )
    equator = overview_scale(sphere, 0, 0)
    sixty_north = overview_scale(sphere, 0, 60)
    assert sixty_north[0] == pytest.approx(equator[0] / 2)
    assert sixty_north[1] == equator[1]
    assert overview_scale(sphere, 0, 90)[0] == 0


def test_overview_pole_edges_have_one_canonical_owner():
    sphere = WorldDefinition(
        seed=42, geometry="sphere", geography="world", radius_m=6000000, overview_resolution=32
    )
    for column in (0, 12.5, 63):
        assert overview_to_world(sphere, column, 0) == (0, 90)
        assert overview_to_world(sphere, column, 32) == (0, -90)
    assert world_to_overview(sphere, 120, 90) == (32, 0)
    assert world_to_overview(sphere, -120, -90) == (32, 32)
