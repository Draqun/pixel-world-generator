"""Generated guides follow the saved contracts and publication guarantees."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from pixel_world.cli import generate
from pixel_world.overview import generate_overview
from pixel_world.params import Params
from pixel_world.regional import Region
from pixel_world.world import WorldDefinition
from pixel_world.writer import create_project, load_project, write_overview, write_region


def snapshots(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def assert_file_table(directory):
    guide = (directory / "README.md").read_text(encoding="utf-8")
    listed = re.findall(r"^\| \[([^]]+)\]\(([^)]+)\) \|", guide, re.MULTILINE)
    assert {name for name, target in listed} == {p.name for p in directory.iterdir() if p.is_file()}
    assert all(name == target for name, target in listed)
    assert guide.endswith("\n")
    return guide


def test_standalone_guide_uses_saved_parameters(tmp_path):
    params = Params(seed=7, size=64, height_range_m=800, sea_level=0.3, erosion_iterations=0)
    generate(params, tmp_path)
    guide = assert_file_table(tmp_path)
    meta = json.loads((tmp_path / "metadata.json").read_bytes())
    assert "64 × 64" in guide and "1 pixel = 1 metre" in guide
    assert str(meta["params"]["height_range_m"]) in guide
    assert str(meta["sea_level_m"]) in guide
    for text in (
        "16-bit",
        "8-bit",
        "little-endian",
        "locally normalized",
        "dark",
        "light",
        "top-left",
        "x right",
        "y down",
        "0 = dry",
        "1 = sea",
        "2 = lake",
        "3 = river",
    ):
        assert text in guide


@pytest.mark.parametrize("geometry", ["flat", "sphere"])
def test_world_guides_match_metadata_and_hashes(tmp_path, geometry):
    world = WorldDefinition(
        seed=7,
        geometry=geometry,
        geography="region",
        width_m=16000 if geometry == "flat" else None,
        height_m=8000 if geometry == "flat" else None,
        radius_m=6000000 if geometry == "sphere" else None,
        height_min_m=-120,
        height_range_m=900,
        sea_level_m=30,
        overview_resolution=16,
        parameters=(("erosion_iterations", 0),),
    )
    create_project(tmp_path / "world", world)
    path = tmp_path / "world"
    root = assert_file_table(path)
    assert "optional" in root and "coverage.json" in root
    region = Region(
        100, 200, 16, 8, **({"anchor_lon": 179.9, "anchor_lat": 20} if geometry == "sphere" else {})
    )
    directory = write_region(path, world, region)
    before = snapshots(path)
    write_overview(path, world, generate_overview(world))
    assert all(
        snapshots(path)[key] == value for key, value in before.items() if key != "coverage.json"
    )
    for area in (directory, path / "overview"):
        guide = assert_file_table(area)
        meta = json.loads((area / "metadata.json").read_bytes())
        assert meta["projection"]["name"] in guide
        for key in ("height_min_m", "height_range_m", "sea_level_m"):
            assert str(meta[key]) in guide
        for omitted in meta["omitted_layers"]:
            assert omitted in guide
        assert "value / 65535" in guide
        assert "top-left" in guide and "x right" in guide and "y down" in guide
    detail = (directory / "README.md").read_text()
    assert "16 × 8" in detail and "(100, 200)" in detail and "1 pixel = 1 metre" in detail
    overview = (path / "overview/README.md").read_text()
    assert f"{meta['columns']} × {meta['rows']}" in overview
    if geometry == "flat":
        assert str(meta["projection"]["pixel_width_m"]) in overview
        assert str(meta["projection"]["pixel_height_m"]) in overview
    else:
        assert "cos(latitude)" in overview and "poles" in overview
        assert str(meta["projection"]["longitude_step_degrees"]) in overview
        regional_meta = json.loads((directory / "metadata.json").read_bytes())
        assert str(regional_meta["projection"]["anchor_lon"]) in detail
        assert str(regional_meta["projection"]["anchor_lat"]) in detail
        assert "distortion" in detail
    for record in load_project(path).coverage:
        guides = [(name, digest) for name, digest in record.artifacts if name.endswith("README.md")]
        assert len(guides) == 1
        name, digest = guides[0]
        assert hashlib.sha256((path / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("kind", ["project", "overview", "region"])
def test_readme_write_failure_cleans_up_and_preserves_previous_files(tmp_path, monkeypatch, kind):
    world = WorldDefinition(
        seed=42,
        geometry="flat",
        geography="region",
        width_m=16000,
        height_m=16000,
        overview_resolution=16,
        parameters=(("erosion_iterations", 0),),
    )
    path = tmp_path / "world"
    if kind != "project":
        create_project(path, world)
        write_region(path, world, Region(0, 0, 8, 8))
    before = snapshots(tmp_path)
    original = Path.open

    def fail_readme(self, mode="r", *args, **kwargs):
        if self.name == "README.md" and "w" in mode:
            # Leave a partial file as a real failed write can do.
            with original(self, "wb") as stream:
                stream.write(b"partial")
            raise OSError("README write failed")
        return original(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_readme)
    with pytest.raises(OSError, match="README write failed"):
        if kind == "project":
            create_project(path, world)
        elif kind == "overview":
            write_overview(path, world, generate_overview(world))
        else:
            write_region(path, world, Region(8, 0, 8, 8))
    assert snapshots(tmp_path) == before
    assert not list(path.rglob(".region-*"))
    if kind == "project":
        assert not path.exists()


def test_old_project_without_guides_is_not_retrofitted(tmp_path):
    world = WorldDefinition(
        seed=42,
        geometry="flat",
        geography="region",
        width_m=16000,
        height_m=16000,
        overview_resolution=16,
        parameters=(("erosion_iterations", 0),),
    )
    create_project(tmp_path / "world", world)
    path = tmp_path / "world"
    write_overview(path, world, generate_overview(world))
    for guide in path.rglob("README.md"):
        guide.unlink()
    coverage = json.loads((path / "coverage.json").read_bytes())
    for area in coverage["areas"]:
        area["artifacts"] = [
            pair for pair in area["artifacts"] if not pair[0].endswith("README.md")
        ]
    (path / "coverage.json").write_text(json.dumps(coverage))
    before = snapshots(path)
    assert load_project(path).definition == world
    directory = write_region(path, world, Region(0, 0, 8, 8))
    assert (directory / "README.md").is_file()
    assert not (path / "README.md").exists()
    assert all(
        snapshots(path)[key] == value for key, value in before.items() if key != "coverage.json"
    )
