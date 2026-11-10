import hashlib
import json
import math
import subprocess

import pytest

from pixel_world import writer
from pixel_world.world import WorldDefinition


def flat(**kwargs):
    return WorldDefinition(
        seed=42, geometry="flat", geography="region", width_m=16000000, height_m=16000000, **kwargs
    )


def hashes(path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir()}


def test_projects_repeat_resume_without_cache_and_remain_independent(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    definition = flat(parameters=(("octaves", 6), ("amplitude", 0.5)))
    writer.create_project(a, definition)
    writer.create_project(b, definition)
    assert hashes(a) == hashes(b)
    before = hashes(a)
    project = writer.load_project(a)
    assert project.definition == definition
    assert project.coverage == ()
    assert not (a / "overview.png").exists()
    result = subprocess.run(
        [
            ".venv/bin/python",
            "-c",
            "from pathlib import Path; from pixel_world.writer import load_project; "
            "import sys; print(load_project(Path(sys.argv[1])).definition.seed)",
            str(a),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "42"
    writer.create_project(
        tmp_path / "other",
        WorldDefinition(seed=7, geometry="sphere", geography="island", radius_m=6000000),
    )
    assert hashes(a) == before


def test_existing_project_and_incompatible_overrides_are_never_overwritten(tmp_path):
    writer.create_project(tmp_path / "world", flat())
    path = tmp_path / "world"
    before = hashes(path)
    with pytest.raises(FileExistsError):
        writer.create_project(path, flat(boundary="wrap_x"))
    with pytest.raises(ValueError, match="incompatible"):
        writer.load_project(path, expected=flat(boundary="wrap_x"))
    assert hashes(path) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 99),
        ("schema_version", True),
        ("generator_version", "999.0.0"),
        ("coordinate_version", 99),
        ("seed", -1),
        ("seed", True),
        ("width_m", 0),
        ("width_m", float("inf")),
        ("height_m", "10"),
        ("geography", "unknown"),
        ("boundary", "unknown"),
        ("radius_m", 5),
        ("sea_level_m", float("nan")),
        ("height_range_m", 0),
        ("overview_resolution", 0),
        ("overview_resolution", True),
        ("parameters", (("x", float("nan")),)),
    ],
)
def test_invalid_definition_rejected_before_writes(tmp_path, field, value):
    values = dict(seed=42, geometry="flat", geography="region", width_m=100, height_m=100)
    values[field] = value
    with pytest.raises(ValueError):
        writer.create_project(tmp_path / "invalid", WorldDefinition(**values))
    assert not (tmp_path / "invalid").exists()


def test_corrupt_manifest_and_unsupported_versions_do_not_change_data(tmp_path):
    path = tmp_path / "world"
    writer.create_project(path, flat())
    manifest = path / "world.json"
    data = json.loads(manifest.read_text())
    data["definition"]["generator_version"] = "999.0.0"
    manifest.write_text(json.dumps(data))
    before = hashes(path)
    with pytest.raises(ValueError, match="version"):
        writer.load_project(path)
    assert hashes(path) == before


def test_definition_identity_is_checked(tmp_path):
    path = tmp_path / "world"
    writer.create_project(path, flat())
    manifest = path / "world.json"
    data = json.loads(manifest.read_text())
    data["definition"]["seed"] = 43
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="identity"):
        writer.load_project(path)


def test_flat_boundaries_and_wrapping():
    assert flat(boundary="wrap_x").flat_position(-1, 2) == (15999999, 2)
    assert flat(boundary="wrap_x").flat_position(16000001, 2) == (1, 2)
    assert flat().flat_position(0, 0) == (0, 0)
    for x, y in ((-1, 0), (16000000, 0), (0, 16000000), (0, -1), (math.nan, 0)):
        with pytest.raises(ValueError):
            flat().flat_position(x, y)
    with pytest.raises(ValueError):
        flat(boundary="wrap_x").flat_position(1, -1)


def test_coverage_is_canonical_and_definition_never_changes(tmp_path):
    from pixel_world.world import CoverageRecord, WorldProject

    definition = flat()
    first, second = tmp_path / "a", tmp_path / "b"
    for path in (first, second):
        writer.create_project(path, definition)
        (path / "a.json").write_bytes(b"area-a")
        (path / "b.json").write_bytes(b"area-b")
    a = CoverageRecord("a", (("a.json", hashlib.sha256(b"area-a").hexdigest()),))
    b = CoverageRecord("b", (("b.json", hashlib.sha256(b"area-b").hexdigest()),))
    original = (first / "world.json").read_bytes()
    writer.write_coverage(first, WorldProject(definition, (b, a)))
    writer.write_coverage(second, WorldProject(definition, (a, b)))
    assert hashes(first) == hashes(second)
    assert (first / "world.json").read_bytes() == original
    assert writer.load_project(first).coverage == (a, b)
    before = hashes(first)
    (first / "b.json").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="hash"):
        writer.write_coverage(first, WorldProject(definition, (a, b)))
    assert (first / "coverage.json").read_bytes() == (second / "coverage.json").read_bytes()
    assert hashlib.sha256((first / "world.json").read_bytes()).hexdigest() == before["world.json"]


@pytest.mark.parametrize(
    "path", ["../escape", "/absolute", "world.json", "./area.json", "a\\b", "."]
)
def test_invalid_coverage_paths(path):
    from pixel_world.world import CoverageRecord

    with pytest.raises(ValueError):
        CoverageRecord("a", ((path, "0" * 64),))


@pytest.mark.parametrize(
    "field,value", [("schema_version", 99), ("world_id", "wrong"), ("areas", {}), ("areas", [None])]
)
def test_invalid_coverage_index_does_not_write(tmp_path, field, value):
    writer.create_project(tmp_path / "world", flat())
    path = tmp_path / "world"
    index = path / "coverage.json"
    data = json.loads(index.read_text())
    data[field] = value
    index.write_text(json.dumps(data))
    before = hashes(path)
    with pytest.raises(ValueError):
        writer.load_project(path)
    assert hashes(path) == before


def test_failed_coverage_publish_leaves_old_index(tmp_path, monkeypatch):
    from pixel_world.world import CoverageRecord, WorldProject

    path = tmp_path / "world"
    writer.create_project(path, flat())
    (path / "region.json").write_bytes(b"metadata")
    record = CoverageRecord("region", (("region.json", hashlib.sha256(b"metadata").hexdigest()),))
    before = hashes(path)

    def fail_publish(*args):
        raise OSError("disk failure")

    monkeypatch.setattr(writer.os, "replace", fail_publish)
    with pytest.raises(OSError, match="disk failure"):
        writer.write_coverage(path, WorldProject(flat(), (record,)))
    assert hashes(path) == before


def test_published_coverage_cannot_be_removed(tmp_path):
    from pixel_world.world import CoverageRecord, WorldProject

    writer.create_project(tmp_path / "world", flat())
    path = tmp_path / "world"
    (path / "region.json").write_bytes(b"metadata")
    record = CoverageRecord("region", (("region.json", hashlib.sha256(b"metadata").hexdigest()),))
    writer.write_coverage(path, WorldProject(flat(), (record,)))
    before = hashes(path)
    with pytest.raises(ValueError, match="removed"):
        writer.write_coverage(path, WorldProject(flat()))
    assert hashes(path) == before


def test_incomplete_manifest_cannot_silently_use_current_defaults(tmp_path):
    path = tmp_path / "world"
    writer.create_project(path, flat())
    manifest = path / "world.json"
    data = json.loads(manifest.read_text())
    del data["definition"]["generator_version"]
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="definition"):
        writer.load_project(path)


def test_coverage_cannot_reference_symlink_outside_project(tmp_path):
    from pixel_world.world import CoverageRecord, WorldProject

    path = tmp_path / "world"
    writer.create_project(path, flat())
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    (path / "link").symlink_to(outside)
    record = CoverageRecord("region", (("link", hashlib.sha256(b"outside").hexdigest()),))
    before = (path / "coverage.json").read_bytes()
    with pytest.raises(ValueError, match="escapes"):
        writer.write_coverage(path, WorldProject(flat(), (record,)))
    assert (path / "coverage.json").read_bytes() == before
