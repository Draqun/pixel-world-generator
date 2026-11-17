"""Serialize generated map layers and metadata."""

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict, fields
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from pixel_world import __version__
from pixel_world.params import Params
from pixel_world.png import write_png8, write_png16
from pixel_world.regional import Region, generate_region, region_metadata
from pixel_world.world import (
    CoverageRecord,
    WorldDefinition,
    WorldProject,
    canonical_json,
)

if TYPE_CHECKING:
    from pixel_world.world_water import HydrologyDefinition


def _file_table(files: dict[str, str]) -> str:
    return "| File | Purpose |\n| --- | --- |\n" + "".join(
        f"| [{name}]({name}) | {purpose} |\n" for name, purpose in sorted(files.items())
    )


def _standalone_readme(params: Params) -> str:
    files = {
        "README.md": "This generated guide.",
        "heightmap.png": "Authoritative 16-bit single-channel grayscale height data.",
        "heightmap.r16": "The same uint16 values, headerless little-endian, row-major.",
        "preview.png": "8-bit grayscale preview only; do not use for terrain heights.",
        "water.png": "8-bit categorical labels: 0 = dry, 1 = sea, 2 = lake, 3 = river.",
        "metadata.json": "Seed, generator version, all parameters and water legend.",
    }
    return f"""# Standalone map

{_file_table(files)}
## Scale and interpretation

All rasters are {params.size} × {params.size} pixels; 1 pixel = 1 metre horizontally.
The origin is top-left, x right and y down. Raw rows use the same orientation.
Height grayscale runs from dark (low) to light (high). Heights are locally normalized
for this standalone map; they do not share a world-project datum.
Decode a 16-bit value as `height_m = value / 65535 * {params.height_range_m}`.
The encoded minimum is 0 m; the full range is {params.height_range_m} m.
Sea level is {params.sea_level * params.height_range_m} m above that minimum;
subtract it for sea-relative elevation. The preview loses height precision.
Water is a label map, not grayscale elevation or water depth.
Biomes, settlements, roads and borders are absent.

This guide is generated deterministically with the data. See metadata.json for the
recorded generation inputs; this directory can be moved without changing the data.
"""


def _world_description(world: WorldDefinition) -> str:
    if world.geometry == "flat":
        dimensions = (
            f"width {world.width_m} m × height {world.height_m} m; {world.boundary} boundary"
        )
    else:
        dimensions = f"radius {world.radius_m} m; complete sphere"
    return (
        f"Geometry: {world.geometry}; {dimensions}.\n"
        f"Geography: {world.geography}; extent: {world.extent}.\n"
    )


def _project_readme(world: WorldDefinition) -> str:
    files = {
        "README.md": "This static generated guide; later exports do not rewrite it.",
        "world.json": (
            "Immutable world definition: identity, seed, versions, dimensions, "
            "datum and parameters."
        ),
        "coverage.json": "Live index of completed areas and their artifact SHA-256 hashes.",
    }
    return f"""# World project

{_world_description(world)}
{_file_table(files)}
The optional `overview/` directory is created only when an overview is exported;
its README.md explains the coarse heightmap.png and metadata.json.
The optional `regions/` directory contains `region-<request-hash>/` exports, each
with README.md, heightmap.png, heightmap.r16 and metadata.json. These directories
may not exist yet. Consult coverage.json for what has actually been generated.

Each export belongs to this saved definition, regardless of export order.
Area guides are generated, hash-indexed artifacts: editing one invalidates its
coverage hash. Older projects without guides remain readable and are not retrofitted.
World-linked water, biomes, settlements, roads and borders are absent.
"""


def _area_readme(world: WorldDefinition, meta: dict) -> str:
    regional = "grid" in meta
    files = {
        "README.md": "This generated, hash-indexed guide; edits invalidate the coverage hash.",
        "heightmap.png": "Authoritative 16-bit single-channel grayscale height samples.",
    }
    if regional:
        files["heightmap.r16"] = "The same uint16 values, headerless little-endian, row-major."
    files["metadata.json"] = (
        "World identity, seed, version, sampling, projection and vertical datum."
    )
    projection = meta["projection"]
    if regional:
        grid = meta["grid"]
        kind = "Regional terrain"
        sampling = (
            f"Dimensions: {grid['width']} × {grid['height']} pixels. Grid origin: "
            f"({grid['x_m']}, {grid['y_m']}) m.\n"
            "Sampling: 1 pixel = 1 metre on the regional grid; samples are at pixel centres.\n"
        )
        if world.geometry == "sphere":
            sampling += (
                f"Projection: {projection['name']}, fixed anchor longitude "
                f"{projection['anchor_lon']}°, latitude {projection['anchor_lat']}°.\n"
                "Maximum scale distortion including erosion context: "
                f"{projection['max_scale_error']}.\n"
                "One-metre grid spacing has projection distortion away from the anchor;\n"
                "see metadata.json projection limits and world corners.\n"
            )
        else:
            sampling += "Projection: flat; the grid uses world metres.\n"
    else:
        kind = "World overview"
        sampling = (
            f"Dimensions: {meta['columns']} × {meta['rows']} pixels. "
            f"Projection: {projection['name']}.\n"
            "This is coarse, projection-dependent sampling at pixel centres.\n"
            "Coastlines between samples and fine terrain are unresolved; samples do not\n"
            "represent uniform land/sea footprints. No regional erosion is applied.\n"
        )
        if world.geometry == "flat":
            sampling += (
                f"Pixel spacing: {projection['pixel_width_m']} m horizontally, "
                f"{projection['pixel_height_m']} m vertically.\n"
            )
        else:
            sampling += (
                f"Longitude step: {projection['longitude_step_degrees']}°; "
                f"latitude step: {projection['latitude_step_degrees']}°.\n"
                "The top edge is 90° N, left edge 180° W; longitude increases right,\n"
                "latitude decreases down. "
                f"Equatorial pixel spacing: {projection['equatorial_pixel_width_m']} m; "
                f"north-south spacing: {projection['pixel_height_m']} m.\n"
                "East-west span = equatorial span * cos(latitude); poles collapse.\n"
            )
    return f"""# {kind}

{_world_description(world)}
{_file_table(files)}
## Scale and interpretation

{sampling}
Image origin is top-left, x right and y down. Height grayscale runs from dark (low)
to light (high), using the shared world encoding, without per-export normalization.
Decode `height_m = {meta["height_min_m"]} + value / 65535 * {meta["height_range_m"]}`.
The encoded minimum is {meta["height_min_m"]} m; the full range is {meta["height_range_m"]} m.
Sea datum is {meta["sea_level_m"]} m; subtract it from height_m for sea-relative elevation.
Sea-datum height shading does not supply a water mask or river network.

Omitted layers: {", ".join(meta["omitted_layers"])}. No world-linked water or exact global
drainage is available. No preview image is exported here.
See metadata.json for the recorded contract and coverage.json at the project root
for artifact hashes. The project definition is world.json; this guide stays unchanged
when neighbours or a later overview are generated.
"""


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

    (out / "README.md").write_text(_standalone_readme(params), encoding="utf-8")


def create_project(
    out: Path, definition: WorldDefinition, *, hydrology: "HydrologyDefinition | None" = None
) -> WorldProject:
    """Create project files without replacing an existing directory or its contents."""
    if not isinstance(definition, WorldDefinition):
        raise ValueError("definition must be a WorldDefinition")
    if hydrology is not None:
        from pixel_world.world_water import HydrologyDefinition

        if not isinstance(hydrology, HydrologyDefinition):
            raise ValueError("hydrology must be a HydrologyDefinition")
        if hydrology.model != "none":
            raise ValueError("enabled world export requires pending terrain conditioning")
    manifest = canonical_json({"world_id": definition.world_id, "definition": definition.to_dict()})
    coverage = canonical_json({"schema_version": 1, "world_id": definition.world_id, "areas": []})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    try:
        (out / "world.json").write_bytes(manifest)
        (out / "coverage.json").write_bytes(coverage)
        (out / "README.md").write_text(_project_readme(definition), encoding="utf-8")
    except OSError:
        for name in ("world.json", "coverage.json", "README.md"):
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
            raise ValueError(
                "incomplete or unknown world definition fields; use the recorded generator"
            )
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


def write_overview(out: Path, definition: WorldDefinition, pixels: NDArray[np.uint16]) -> None:
    """Publish an overview once and index its completed artifacts, preserving old project data."""
    from pixel_world.overview import overview_metadata
    from pixel_world.png import encode_png

    project = load_project(out, expected=definition)
    meta = overview_metadata(definition, pixels)
    metadata = canonical_json(meta)
    image = encode_png(pixels)
    if any(record.area_id == "overview" for record in project.coverage):
        raise FileExistsError("overview already registered")
    directory = out / "overview"
    directory.mkdir()
    files = {
        "heightmap.png": image,
        "metadata.json": metadata,
        "README.md": _area_readme(definition, meta).encode("utf-8"),
    }
    try:
        for name, data in files.items():
            (directory / name).write_bytes(data)
        record = CoverageRecord(
            "overview",
            tuple(
                (f"overview/{name}", hashlib.sha256(data).hexdigest())
                for name, data in files.items()
            ),
        )
        write_coverage(out, WorldProject(definition, (*project.coverage, record)))
    except (OSError, ValueError):
        for name in files:
            (directory / name).unlink(missing_ok=True)
        directory.rmdir()
        raise


def write_region(
    out: Path, definition: WorldDefinition, region: Region, *, water: str = "none"
) -> Path:
    """Publish complete terrain artifacts once, then register their hashes atomically."""
    from pixel_world.png import encode_png

    project = load_project(out, expected=definition)
    meta = region_metadata(definition, region, water=water)
    metadata = canonical_json(meta)
    area_id = "region-" + hashlib.sha256(metadata).hexdigest()
    directory = out / "regions" / area_id
    if not directory.resolve().is_relative_to(out.resolve()):
        raise ValueError("artifact escapes the project directory")
    if directory.exists() or any(record.area_id == area_id for record in project.coverage):
        raise FileExistsError("region already exists; select another area or use a fresh project")
    pixels = generate_region(definition, region)
    files = {
        "heightmap.png": encode_png(pixels),
        "heightmap.r16": pixels.astype("<u2").tobytes(),
        "metadata.json": metadata,
        "README.md": _area_readme(definition, meta).encode("utf-8"),
    }
    parent_existed = directory.parent.exists()
    directory.parent.mkdir(exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".region-", dir=directory.parent))
    published = False
    try:
        for name, data in files.items():
            with (staged / name).open("wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        os.replace(staged, directory)
        published = True
        record = CoverageRecord(
            area_id,
            tuple(
                (f"regions/{area_id}/{name}", hashlib.sha256(data).hexdigest())
                for name, data in files.items()
            ),
        )
        write_coverage(out, WorldProject(definition, (*project.coverage, record)))
    except BaseException:
        # A signal can arrive after the atomic index commit; indexed files must survive.
        if published and any(r.area_id == area_id for r in load_project(out).coverage):
            raise
        shutil.rmtree(directory if published else staged)
        if not parent_existed:
            directory.parent.rmdir()
        raise
    return directory
