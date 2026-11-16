"""Coordinate-keyed terrain refinement and bounded, world-aligned metre grids."""

import math
from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray

from pixel_world.coordinates import MAX_SCALE_ERROR, projection_scale_error
from pixel_world.erosion import SWEEPS, erode
from pixel_world.overview import ROW_BATCH, geography_field, overview_shape
from pixel_world.seeds import step_rng
from pixel_world.world import WorldDefinition, finite

MAX_REGION_SAMPLES = 1_048_576
MAX_COORDINATE_M = 2**50
DETAIL_SPACING_M = (512, 128, 32, 8)
DEFAULT_CONTROLS = {
    "detail_amplitude_m": 8.0,
    "erosion_iterations": 0,
    "erosion_strength": 0.02,
    "erosion_talus": 0.01,
}


@dataclass(frozen=True)
class Region:
    """Integer metre edges on a fixed flat or anchored east/right, south/down grid."""

    x_m: int
    y_m: int
    width: int
    height: int
    anchor_lon: float | None = None
    anchor_lat: float | None = None

    def __post_init__(self) -> None:
        for name in ("x_m", "y_m", "width", "height"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer in metres")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("region dimensions must be positive")
        if max(abs(self.x_m), abs(self.y_m), self.width, self.height) > MAX_COORDINATE_M:
            raise ValueError("region exceeds coordinate precision limit of 2**50 metres")
        if (self.anchor_lon is None) != (self.anchor_lat is None):
            raise ValueError("provide both projection anchor coordinates")
        if self.anchor_lon is not None:
            finite(self.anchor_lon, "anchor_lon")
            finite(self.anchor_lat, "anchor_lat")
            if not -90 <= self.anchor_lat <= 90:
                raise ValueError("anchor latitude must be in [-90, 90]")
            lon = 0.0 if abs(self.anchor_lat) == 90 else (self.anchor_lon + 180) % 360 - 180
            object.__setattr__(self, "anchor_lon", float(lon))
            object.__setattr__(self, "anchor_lat", float(self.anchor_lat))


def regional_controls(world: WorldDefinition) -> dict:
    """Validate the complete supported regional model before allocating or writing."""
    controls = DEFAULT_CONTROLS | dict(world.parameters)
    if set(controls) != set(DEFAULT_CONTROLS):
        raise ValueError("unsupported regional parameter; see documented regional controls")
    iterations = controls["erosion_iterations"]
    if type(iterations) is not int or not 0 <= iterations <= 64:
        raise ValueError("erosion_iterations must be an integer in [0, 64]")
    for name in ("detail_amplitude_m", "erosion_strength", "erosion_talus"):
        finite(controls[name], name)
        if controls[name] < 0:
            raise ValueError(f"{name} must be non-negative")
    if controls["detail_amplitude_m"] > world.height_range_m:
        raise ValueError("detail_amplitude_m must not exceed height_range_m")
    if controls["erosion_strength"] > 1 or controls["erosion_talus"] > 1:
        raise ValueError("erosion_strength and erosion_talus must be in [0, 1]")
    dimensions = (
        (world.radius_m,) if world.geometry == "sphere" else (world.width_m, world.height_m)
    )
    if max(dimensions) > MAX_COORDINATE_M:
        raise ValueError("world exceeds regional coordinate precision limit of 2**50 metres")
    return controls


def _hash_noise(indices: tuple, salt: np.uint64) -> NDArray[np.float64]:
    key = np.full(np.broadcast_shapes(*(i.shape for i in indices)), salt, dtype=np.uint64)
    with np.errstate(over="ignore"):
        for index, prime in zip(
            indices, (0x9E3779B185EBCA87, 0xC2B2AE3D27D4EB4F, 0x165667B19E3779F9), strict=False
        ):
            key ^= index.astype(np.uint64) * np.uint64(prime)
        key ^= key >> np.uint64(30)
        key *= np.uint64(0xBF58476D1CE4E5B9)
        key ^= key >> np.uint64(27)
        key *= np.uint64(0x94D049BB133111EB)
        key ^= key >> np.uint64(31)
    return (key >> np.uint64(11)).astype(np.float64) / 2**52 - 1


def _value_noise(coordinates: tuple, salt: np.uint64, period: int | None) -> NDArray:
    lower = tuple(np.floor(c).astype(np.int64) for c in coordinates)
    blends = tuple(
        (c - i) ** 2 * (3 - 2 * (c - i)) for c, i in zip(coordinates, lower, strict=True)
    )
    noise = np.zeros_like(coordinates[0])
    for corner in range(2 ** len(coordinates)):
        indices, weight = [], np.ones_like(noise)
        for axis, (index, blend) in enumerate(zip(lower, blends, strict=True)):
            upper = (corner >> axis) & 1
            value = index + upper
            indices.append(value % period if axis == 0 and period is not None else value)
            weight *= blend if upper else 1 - blend
        noise += weight * _hash_noise(tuple(indices), salt)
    return noise


def _anchor_gate(world: WorldDefinition, first: NDArray, second: NDArray) -> NDArray:
    rows, cols = overview_shape(world)
    if world.geometry == "flat":
        first = first % world.width_m if world.boundary == "wrap_x" else first
        u, v = first / world.width_m * cols - 0.5, second / world.height_m * rows - 0.5
    else:
        u = ((first + 180) % 360) / 360 * cols - 0.5
        v = (90 - second) / 180 * rows - 0.5
    # Reduce before sin so every reference centre is exactly zero, including roundoff.
    du, dv = u - np.rint(u), v - np.rint(v)
    du, dv = np.where(abs(du) < 1e-10, 0, du), np.where(abs(dv) < 1e-10, 0, dv)
    gate = (np.sin(np.pi * du) ** 2 + np.sin(np.pi * dv) ** 2) / 2
    if world.geometry == "sphere":
        gate *= np.where(abs(second) == 90, 0, np.cos(np.deg2rad(second)) ** 2)
    return gate


def _terrain_field(world: WorldDefinition, first: NDArray, second: NDArray) -> NDArray:
    controls = regional_controls(world)
    first, second = np.broadcast_arrays(
        np.asarray(first, dtype=float), np.asarray(second, dtype=float)
    )
    coarse = geography_field(world, first, second, step_rng(world.seed, "world.geography"))
    salts = step_rng(world.seed, "world.detail").integers(0, 2**64, size=4, dtype=np.uint64)
    detail = np.zeros_like(coarse)
    if world.geometry == "flat":
        first = first % world.width_m if world.boundary == "wrap_x" else first
    else:
        lon, lat = np.deg2rad((first + 180) % 360 - 180), np.deg2rad(second)
        cosine = np.where(abs(second) == 90, 0, np.cos(lat))
        direction = (cosine * np.cos(lon), cosine * np.sin(lon), np.sin(lat))
    for level, (spacing, salt) in enumerate(zip(DETAIL_SPACING_M, salts, strict=True)):
        period = None
        if world.geometry == "flat":
            period = max(1, math.ceil(world.width_m / spacing))
            coordinates = (first / world.width_m * period, second / spacing)
        else:
            coordinates = tuple(d * (world.radius_m / spacing) for d in direction)
        detail += 0.5**level * _value_noise(coordinates, salt, period)
    detail *= controls["detail_amplitude_m"] / world.height_range_m / 1.875
    return np.clip(coarse + _anchor_gate(world, first, second) * detail, 0, 1)


def terrain_samples(world: WorldDefinition, first: NDArray, second: NDArray) -> NDArray[np.uint16]:
    """Un-eroded uint16 terrain at metres (flat) or longitude/latitude degrees (sphere)."""
    return np.rint(_terrain_field(world, first, second) * 65535).astype(np.uint16)


def region_context(world: WorldDefinition, region: Region) -> tuple[int, float]:
    """Preflight output/context budgets and return halo cells and maximum projection scale error."""
    controls = regional_controls(world)
    # Twelve-hop accumulation + target selection + two-hop thermal transfer, then fixed ring.
    iterations = controls["erosion_iterations"]
    halo = (SWEEPS + 3) * iterations + 1 if iterations else 0
    if (region.width + 2 * halo) * (region.height + 2 * halo) > MAX_REGION_SAMPLES:
        raise ValueError(
            "region/context exceeds 1048576-sample budget; reduce size or erosion iterations"
        )
    if world.geometry == "flat":
        if region.anchor_lon is not None:
            raise ValueError("flat regions must not specify a spherical anchor")
        if (
            region.y_m < 0
            or region.y_m + region.height > world.height_m
            or (
                world.boundary == "bounded"
                and (region.x_m < 0 or region.x_m + region.width > world.width_m)
            )
        ):
            raise ValueError("region lies outside the bounded world")
        if region.width > world.width_m:
            raise ValueError("region width must not exceed the world circumference")
        return halo, 0.0
    if region.anchor_lon is None:
        raise ValueError("spherical region requires a fixed projection anchor")
    distance = math.hypot(
        max(abs(region.x_m - halo), abs(region.x_m + region.width + halo)),
        max(abs(region.y_m - halo), abs(region.y_m + region.height + halo)),
    )
    error = projection_scale_error(distance, world.radius_m)
    if error > MAX_SCALE_ERROR:
        raise ValueError(
            "local projection distortion including erosion context exceeds 1%; reduce area"
        )
    return halo, error


def _positions(world: WorldDefinition, region: Region, x: NDArray, y: NDArray) -> tuple:
    x, y = np.broadcast_arrays(x, y)
    if world.geometry == "flat":
        x = (
            x % world.width_m
            if world.boundary == "wrap_x"
            else np.clip(x, 0, np.nextafter(world.width_m, 0))
        )
        return x, np.clip(y, 0, np.nextafter(world.height_m, 0))
    lon, lat = math.radians(region.anchor_lon), math.radians(region.anchor_lat)
    # Match the canonical pole basis used by local_to_lonlat.
    cosine = 0.0 if abs(region.anchor_lat) == 90 else math.cos(lat)
    origin = (cosine * math.cos(lon), cosine * math.sin(lon), math.sin(lat))
    east = (-math.sin(lon), math.cos(lon), 0)
    north = (-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat))
    distance = np.hypot(x, y)
    angle = distance / world.radius_m
    factor = np.sinc(angle / np.pi) / world.radius_m
    a, b, c = (np.cos(angle) * origin[i] + factor * (x * east[i] - y * north[i]) for i in range(3))
    longitude = (np.rad2deg(np.arctan2(b, a)) + 180) % 360 - 180
    longitude = np.where(np.hypot(a, b) < 1e-15, 0, longitude)
    return longitude, np.rad2deg(np.arctan2(c, np.hypot(a, b)))


def generate_region(world: WorldDefinition, region: Region) -> NDArray[np.uint16]:
    """Generate only the requested grid and proven context; never depend on project coverage."""
    halo, _ = region_context(world, region)
    controls = regional_controls(world)
    rows, columns = region.height + 2 * halo, region.width + 2 * halo
    height = np.empty((rows, columns), dtype=np.float64)
    x = region.x_m + np.arange(-halo, region.width + halo, dtype=np.float64) + 0.5
    for start in range(0, rows, ROW_BATCH):
        y = (
            region.y_m
            + np.arange(start - halo, min(start + ROW_BATCH, rows) - halo, dtype=np.float64)
            + 0.5
        )
        first, second = _positions(world, region, x[None, :], y[:, None])
        height[start : start + len(y)] = _terrain_field(world, first, second)
    if halo:
        height = erode(
            height,
            controls["erosion_iterations"],
            controls["erosion_strength"],
            controls["erosion_talus"],
        )
    height = height[halo : halo + region.height, halo : halo + region.width].copy()
    if halo:
        # Restore every coarse anchor without fitting constraints to this output's bounds.
        for start in range(0, region.height, ROW_BATCH):
            y = (
                region.y_m
                + np.arange(start, min(start + ROW_BATCH, region.height), dtype=float)
                + 0.5
            )
            first, second = _positions(
                world, region, x[None, halo : halo + region.width], y[:, None]
            )
            original = _terrain_field(world, first, second)
            target = height[start : start + len(y)]
            target[:] = original + _anchor_gate(world, first, second) * (target - original)
    return np.rint(np.clip(height, 0, 1) * 65535).astype(np.uint16)


def region_metadata(world: WorldDefinition, region: Region) -> dict:
    """Describe a fixed projection, world provenance, vertical encoding and omitted layers."""
    halo, error = region_context(world, region)
    rows, cols = overview_shape(world)
    corners = [
        _positions(world, region, np.array(float(x)), np.array(float(y)))
        for x in (region.x_m, region.x_m + region.width)
        for y in (region.y_m, region.y_m + region.height)
    ]
    return {
        "world_id": world.world_id,
        "seed": world.seed,
        "generator_version": world.generator_version,
        "geometry": world.geometry,
        "coordinate_version": world.coordinate_version,
        "geography": world.geography,
        "grid": asdict(region),
        "sample_spacing_m": 1,
        "sampling": "pixel centres at (x_m+column+0.5, y_m+row+0.5); x right, y down",
        "height_min_m": world.height_min_m,
        "height_range_m": world.height_range_m,
        "sea_level_m": world.sea_level_m,
        "encoding": (
            "uint16; height_m = height_min_m + value/65535*height_range_m; R16 little-endian"
        ),
        "world_dimensions": {
            "width_m": world.width_m,
            "height_m": world.height_m,
            "radius_m": world.radius_m,
            "boundary": world.boundary,
        },
        "parameters": regional_controls(world),
        "projection": {
            "name": "flat" if world.geometry == "flat" else "azimuthal-equidistant",
            "anchor_lon": region.anchor_lon,
            "anchor_lat": region.anchor_lat,
            "max_scale_error": error,
            "includes_context": True,
            "world_corners": [[float(a), float(b)] for a, b in corners],
        },
        "overview": {
            "rows": rows,
            "columns": cols,
            "sampling": (
                "flat: ((column+0.5)*width_m/columns, (row+0.5)*height_m/rows); "
                "sphere: (-180+360*(column+0.5)/columns, 90-180*(row+0.5)/rows)"
            ),
            "unresolved_detail": "overview coastlines between anchors are unresolved",
        },
        "terrain": {
            "field": "anchored-hierarchical-value-noise-v1",
            "spacing_m": DETAIL_SPACING_M,
            "step": "world.detail",
        },
        "erosion": {
            "model": "12-hop-stream-power-and-thermal-v1",
            "halo_cells": halo,
            "exact_global_drainage": False,
            "anchor_displacement_gated": True,
        },
        "omitted_layers": ["water", "biomes", "settlements", "roads", "borders"],
    }
