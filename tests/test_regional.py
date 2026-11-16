import hashlib
import json
from dataclasses import replace

import numpy as np
import pytest

from pixel_world.coordinates import cube_to_lonlat, local_to_lonlat, surface_distance
from pixel_world.overview import generate_overview, geography_field, overview_to_world
from pixel_world.png import read_png
from pixel_world.regional import Region, generate_region, terrain_samples
from pixel_world.seeds import step_rng
from pixel_world.world import WorldDefinition
from pixel_world.writer import create_project, load_project, write_overview, write_region


def flat(**kwargs):
    defaults = dict(
        seed=42,
        geometry="flat",
        geography="region",
        width_m=16000000,
        height_m=16000000,
        overview_resolution=32,
    )
    return WorldDefinition(**(defaults | kwargs))


def sphere(**kwargs):
    defaults = dict(
        seed=42, geometry="sphere", geography="world", radius_m=6000000, overview_resolution=32
    )
    return WorldDefinition(**(defaults | kwargs))


def hashes(path):
    return {
        str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in path.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("world", [flat(), sphere()])
def test_every_overview_anchor_is_preserved_without_an_image(world):
    overview = generate_overview(world)
    for row in range(overview.shape[0]):
        x, y = np.array(
            [overview_to_world(world, col + 0.5, row + 0.5) for col in range(overview.shape[1])]
        ).T
        assert np.array_equal(terrain_samples(world, x, y), overview[row])


def test_refinement_has_detail_seed_isolation_and_shared_datum():
    world = flat(geography="island")
    x = np.arange(1024) + 8000000.5
    y = np.full_like(x, 8000000.5)
    actual = terrain_samples(world, x, y)
    coarse = geography_field(world, x, y, step_rng(world.seed, "world.geography"))
    assert not np.array_equal(actual, np.rint(coarse * 65535).astype(np.uint16))
    assert not np.array_equal(actual, terrain_samples(replace(world, seed=43), x, y))
    step_rng(42, "future.water").random(100)
    assert np.array_equal(actual, terrain_samples(world, x, y))
    assert 0 < actual.min() < actual.max() < 65535
    assert np.array_equal(actual[100:200], terrain_samples(world, x[100:200], y[100:200]))


@pytest.mark.parametrize(
    "world,region",
    [
        (flat(), Region(8000000, 8000000, 48, 32)),
        (flat(width_m=128, height_m=128, boundary="wrap_x"), Region(110, 20, 48, 32)),
        (sphere(), Region(-24, -16, 48, 32, anchor_lon=45, anchor_lat=0)),
        (sphere(), Region(-24, -16, 48, 32, anchor_lon=180, anchor_lat=0)),
        (sphere(), Region(-24, -16, 48, 32, anchor_lon=10, anchor_lat=90)),
    ],
)
@pytest.mark.parametrize("iterations", [0, 1, 3])
def test_partitions_overlaps_and_eroded_seams(world, region, iterations):
    world = replace(world, parameters=(("erosion_iterations", iterations),))
    whole = generate_region(world, region)
    left = generate_region(world, replace(region, width=24))
    right = generate_region(world, replace(region, x_m=region.x_m + 24, width=24))
    overlap = generate_region(world, replace(region, x_m=region.x_m + 10, width=20))
    assert np.array_equal(whole, np.concatenate((left, right), axis=1))
    assert np.array_equal(whole[:, 10:30], overlap)
    assert whole.dtype == np.uint16


def test_wrap_cube_faces_and_poles_share_samples():
    world = flat(width_m=128, height_m=128, boundary="wrap_x")
    assert np.array_equal(
        generate_region(world, Region(-10, 10, 20, 20)),
        generate_region(world, Region(118, 10, 20, 20)),
    )
    world = sphere()
    a = cube_to_lonlat("+x", 1, 0.25)
    b = cube_to_lonlat("+y", -1, 0.25)
    assert terrain_samples(world, *a) == terrain_samples(world, *b)
    assert terrain_samples(world, -180, 20) == terrain_samples(world, 180, 20)
    assert terrain_samples(world, -40, 90) == terrain_samples(world, 120, 90)
    # No face/longitude seam jump between points less than a metre apart.
    for lon in (45, 180):
        a, b = terrain_samples(world, np.array([lon - 1e-6, lon + 1e-6]), 0)
        assert abs(int(a) - int(b)) <= 1


def test_erosion_changes_detail_and_preserves_anchor_grid():
    world = flat(width_m=65, height_m=65, overview_resolution=5)
    eroded = replace(world, parameters=(("erosion_iterations", 2),))
    plain = generate_region(world, Region(0, 0, 65, 65))
    result = generate_region(eroded, Region(0, 0, 65, 65))
    assert not np.array_equal(result, plain)
    assert np.array_equal(result[6::13, 6::13], generate_overview(eroded))


def test_disabled_erosion_transfers_do_not_change_refinement():
    world = flat(width_m=128, height_m=128, geography="island")
    disabled = replace(
        world, parameters=(("erosion_iterations", 2), ("erosion_strength", 0), ("erosion_talus", 1))
    )
    region = Region(30, 30, 32, 32)
    assert np.array_equal(generate_region(world, region), generate_region(disabled, region))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width": 0},
        {"height": -1},
        {"x_m": 0.5},
        {"width": True},
        {"anchor_lon": float("nan"), "anchor_lat": 0},
        {"anchor_lon": 0},
        {"anchor_lon": 0, "anchor_lat": 91},
    ],
)
def test_invalid_grid(kwargs):
    with pytest.raises(ValueError):
        Region(**(dict(x_m=0, y_m=0, width=16, height=16) | kwargs))


@pytest.mark.parametrize(
    "world,region,match",
    [
        (flat(), Region(-1, 0, 16, 16), "outside"),
        (flat(), Region(15999999, 0, 16, 16), "outside"),
        (flat(), Region(0, 0, 1025, 1024), "budget"),
        (sphere(), Region(0, 0, 16, 16), "anchor"),
        (flat(), Region(0, 0, 16, 16, anchor_lon=0, anchor_lat=0), "anchor"),
        (sphere(radius_m=1000), Region(1000, 0, 16, 16, anchor_lon=0, anchor_lat=0), "distortion"),
        (flat(parameters=(("erosion_iterations", 64),)), Region(0, 0, 16, 16), "budget"),
        (flat(parameters=(("erosion_iterations", 1.5),)), Region(0, 0, 16, 16), "iterations"),
        (flat(parameters=(("erosion_strength", -1),)), Region(0, 0, 16, 16), "strength"),
        (flat(parameters=(("unknown", 1),)), Region(0, 0, 16, 16), "unsupported"),
        (flat(width_m=2**55), Region(0, 0, 16, 16), "precision"),
    ],
)
def test_preflight_errors_leave_project_untouched(tmp_path, world, region, match):
    create_project(tmp_path / "world", world)
    before = hashes(tmp_path)
    with pytest.raises(ValueError, match=match):
        write_region(tmp_path / "world", world, region)
    assert hashes(tmp_path) == before


@pytest.mark.parametrize(
    "world,region",
    [
        (flat(), Region(100, 200, 32, 24)),
        (sphere(), Region(-16, -12, 32, 24, anchor_lon=179.999, anchor_lat=60)),
    ],
)
def test_export_reopen_orders_hashes_alignment_and_metadata(tmp_path, world, region):
    expected = generate_region(world, region)
    neighbour = replace(region, x_m=region.x_m + region.width)
    for name, order in (("a", (region, neighbour)), ("b", (neighbour, region))):
        path = tmp_path / name
        create_project(path, world)
        manifest = (path / "world.json").read_bytes()
        for request in order:
            before = hashes(path / "regions")
            write_region(path, load_project(path).definition, request)
            assert all(hashes(path / "regions")[k] == v for k, v in before.items())
        assert manifest == (path / "world.json").read_bytes()
        assert len(load_project(path).coverage) == 2
    assert hashes(tmp_path / "a") == hashes(tmp_path / "b")
    for directory in (tmp_path / "a/regions").iterdir():
        meta = json.loads((directory / "metadata.json").read_bytes())
        png, depth, _ = read_png(directory / "heightmap.png")
        raw = np.fromfile(directory / "heightmap.r16", dtype="<u2").reshape(png.shape)
        assert depth == 16 and np.array_equal(png, raw)
        assert meta["world_id"] == world.world_id
        assert meta["sample_spacing_m"] == 1
        assert meta["height_range_m"] == world.height_range_m
        assert meta["omitted_layers"] == ["water", "biomes", "settlements", "roads", "borders"]
        assert 0 <= meta["projection"]["max_scale_error"] <= 0.01
        if meta["grid"]["x_m"] == region.x_m:
            assert np.array_equal(expected, png)
    before = hashes(tmp_path / "a")
    with pytest.raises(FileExistsError):
        write_region(tmp_path / "a", world, region)
    assert hashes(tmp_path / "a") == before


def test_overview_before_or_after_region_preserves_every_file(tmp_path):
    world = flat()
    for name in ("first", "last"):
        path = tmp_path / name
        create_project(path, world)
        if name == "first":
            write_overview(path, world, generate_overview(world))
        write_region(path, world, Region(125000, 125000, 16, 16))
        if name == "last":
            previous = hashes(path / "regions")
            write_overview(path, world, generate_overview(world))
            assert hashes(path / "regions") == previous
    assert hashes(tmp_path / "first") == hashes(tmp_path / "last")


@pytest.mark.parametrize("failure", ["file", "directory", "index"])
def test_interrupted_export_leaves_prior_artifacts_and_coverage(tmp_path, monkeypatch, failure):
    import pixel_world.writer as writer

    world = flat()
    path = tmp_path / "world"
    create_project(path, world)
    write_region(path, world, Region(100, 100, 16, 16))
    before = hashes(path)
    original_open = writer.Path.open
    original_replace = writer.os.replace

    def fail_open(self, mode="r", *args, **kwargs):
        if self.name == "heightmap.r16" and mode == "wb":
            raise OSError("interrupted file")
        return original_open(self, mode, *args, **kwargs)

    def fail_replace(src, dst):
        if (failure == "index") == (writer.Path(dst).name == "coverage.json"):
            raise OSError("interrupted publication")
        return original_replace(src, dst)

    if failure == "file":
        monkeypatch.setattr(writer.Path, "open", fail_open)
    else:
        monkeypatch.setattr(writer.os, "replace", fail_replace)
    with pytest.raises(OSError):
        write_region(path, world, Region(116, 100, 16, 16))
    assert hashes(path) == before
    assert len(list((path / "regions").iterdir())) == 1


def test_spherical_pixel_distance_and_distortion_include_context():
    world = sphere()
    a = local_to_lonlat(45, 60, 0.5, 0.5, world.radius_m)
    b = local_to_lonlat(45, 60, 1.5, 0.5, world.radius_m)
    assert surface_distance(*a, *b, world.radius_m) == pytest.approx(1, abs=1e-8)
    # Output is inside tolerance but its required erosion context is outside.
    world = sphere(radius_m=1000, parameters=(("erosion_iterations", 1),))
    with pytest.raises(ValueError, match="distortion"):
        generate_region(world, Region(230, 0, 1, 1, anchor_lon=0, anchor_lat=0))


@pytest.mark.parametrize("iterations", [0, 2])
def test_allocation_bound_is_independent_of_physical_world_size(monkeypatch, iterations):
    import pixel_world.regional as regional

    original = regional.geography_field
    shapes = []

    def measured(world, first, second, rng):
        shapes.append(np.broadcast_shapes(np.shape(first), np.shape(second)))
        return original(world, first, second, rng)

    monkeypatch.setattr(regional, "geography_field", measured)
    calls = []
    halo = 15 * iterations + 1 if iterations else 0
    for size in (16000, 16000000):
        shapes.clear()
        world = flat(width_m=size, height_m=size, parameters=(("erosion_iterations", iterations),))
        generate_region(world, Region(100, 100, 128, 96))
        assert max(np.prod(shape) for shape in shapes) <= 64 * (128 + 2 * halo)
        calls.append(shapes.copy())
    assert calls[0] == calls[1]


def test_export_refuses_regions_symlink_outside_project(tmp_path, monkeypatch):
    import pixel_world.writer as writer

    world = flat()
    path, external = tmp_path / "world", tmp_path / "external"
    create_project(path, world)
    external.mkdir()
    (path / "regions").symlink_to(external, target_is_directory=True)
    before = hashes(tmp_path)

    def unexpected_sampling(*args):
        pytest.fail("unsafe artifact path must fail before sampling or writing")

    monkeypatch.setattr(writer, "generate_region", unexpected_sampling)
    with pytest.raises(ValueError, match="escapes"):
        write_region(path, world, Region(0, 0, 16, 16))
    assert hashes(tmp_path) == before


def test_interrupt_after_coverage_commit_keeps_indexed_artifacts(tmp_path, monkeypatch):
    import pixel_world.writer as writer

    world = flat()
    path = tmp_path / "world"
    create_project(path, world)
    write_region(path, world, Region(0, 0, 16, 16))
    previous = hashes(path / "regions")
    original_replace = writer.os.replace

    def interrupt_after_commit(src, dst):
        original_replace(src, dst)
        if writer.Path(dst).name == "coverage.json":
            raise KeyboardInterrupt

    monkeypatch.setattr(writer.os, "replace", interrupt_after_commit)
    with pytest.raises(KeyboardInterrupt):
        write_region(path, world, Region(16, 0, 16, 16))
    project = load_project(path)
    assert len(project.coverage) == 2
    for record in project.coverage:
        for name, digest in record.artifacts:
            assert hashlib.sha256((path / name).read_bytes()).hexdigest() == digest
    assert all(hashes(path / "regions")[k] == v for k, v in previous.items())
