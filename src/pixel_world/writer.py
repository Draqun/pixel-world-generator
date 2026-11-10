"""Serialize generated map layers and metadata."""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, fields
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from pixel_world import __version__
from pixel_world.params import Params
from pixel_world.png import write_png8, write_png16
from pixel_world.world import (
    CoverageRecord,
    WorldDefinition,
    WorldProject,
    canonical_json,
)


def write_world(
    out: Path, height: NDArray[np.uint16], water: NDArray[np.uint8], params: Params
) -> None:
    """Write aligned terrain and water layers with their generation parameters."""
    preview = ((height.astype(np.uint32) + 128) // 257).astype(np.uint8)
    fields = params.to_dict()
    meta = {
        "generator_version": __version__,
        "seed": fields.pop("seed"),
        "params": fields,
        "sea_level_m": params.sea_level * params.height_range_m,
        "layers": {"water.png": {"0": "dry", "1": "sea", "2": "lake", "3": "river"}},
    }
    out.mkdir(parents=True, exist_ok=True)
    write_png16(out / "heightmap.png", height)
    (out / "heightmap.r16").write_bytes(height.astype("<u2").tobytes())
    write_png8(out / "preview.png", preview)
    write_png8(out / "water.png", water)
    (out / "metadata.json").write_text(
        json.dumps(meta, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def create_project(out: Path, definition: WorldDefinition) -> WorldProject:
    """Create project files without replacing an existing directory or its contents."""
    if not isinstance(definition, WorldDefinition):
        raise ValueError("definition must be a WorldDefinition")
    manifest = canonical_json({"world_id": definition.world_id, "definition": definition.to_dict()})
    coverage = canonical_json({"schema_version": 1, "world_id": definition.world_id, "areas": []})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    try:
        (out / "world.json").write_bytes(manifest)
        (out / "coverage.json").write_bytes(coverage)
    except OSError:
        for name in ("world.json", "coverage.json"):
            (out / name).unlink(missing_ok=True)
        out.rmdir()
        raise
    return WorldProject(definition)


def load_project(out: Path, expected: WorldDefinition | None = None) -> WorldProject:
    """Read validated state; mismatched settings and unsupported versions never mutate files."""
    try:
        manifest = json.loads((out / "world.json").read_text(encoding="utf-8"))
        if set(manifest) != {"world_id", "definition"}:
            raise ValueError("invalid world manifest")
        if not isinstance(manifest["definition"], dict) or set(manifest["definition"]) != {
            field.name for field in fields(WorldDefinition)
        }:
            raise ValueError("incomplete or unknown world definition fields")
        definition = WorldDefinition(**manifest["definition"])
        if manifest["world_id"] != definition.world_id:
            raise ValueError("world identity does not match definition")
        if expected is not None and expected != definition:
            raise ValueError("incompatible project settings; create a new project instead")
        index = json.loads((out / "coverage.json").read_text(encoding="utf-8"))
        if (
            set(index) != {"schema_version", "world_id", "areas"}
            or type(index["schema_version"]) is not int
            or index["schema_version"] != 1
            or index["world_id"] != definition.world_id
            or not isinstance(index["areas"], list)
        ):
            raise ValueError("invalid or incompatible coverage index")
        records = tuple(CoverageRecord(**area) for area in index["areas"])
        return WorldProject(definition, records)
    except (TypeError, KeyError, AttributeError) as error:
        raise ValueError("invalid project data") from error


def write_coverage(out: Path, project: WorldProject) -> None:
    """Atomically index complete artifacts without touching the immutable world manifest."""
    # shortcut: writes require one process per project; add locking before parallel generation.
    existing = load_project(out, expected=project.definition)
    records = {record.area_id: record for record in project.coverage}
    if any(records.get(record.area_id) != record for record in existing.coverage):
        raise ValueError("existing coverage cannot be removed or replaced")
    for record in project.coverage:
        for name, digest in record.artifacts:
            path = out / name
            if not path.resolve().is_relative_to(out.resolve()):
                raise ValueError("artifact escapes the project directory")
            with path.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != digest:
                raise ValueError(f"artifact hash mismatch: {name}")
    payload = canonical_json(
        {
            "schema_version": 1,
            "world_id": project.definition.world_id,
            "areas": [asdict(record) for record in project.coverage],
        }
    )
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=out, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, out / "coverage.json")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
