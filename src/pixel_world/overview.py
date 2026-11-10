"""World-space coarse geography and a bounded overview sampling lattice."""

import math

import numpy as np
from numpy.typing import NDArray

from pixel_world.seeds import step_rng
from pixel_world.world import WorldDefinition, finite

MAX_OVERVIEW_SAMPLES = 1_048_576
ROW_BATCH = 64


def overview_shape(world: WorldDefinition) -> tuple[int, int]:
    """Return rows/columns without allocating a raster; enforce the overview budget."""
    n = world.overview_resolution
    if world.geometry == "sphere":
        rows, columns = n, 2 * n
    elif world.width_m >= world.height_m:
        rows, columns = max(1, round(n * (world.height_m / world.width_m))), n
    else:
        rows, columns = n, max(1, round(n * (world.width_m / world.height_m)))
    if rows * columns > MAX_OVERVIEW_SAMPLES:
        raise ValueError("overview exceeds 1048576 samples; lower overview_resolution")
    return rows, columns


def overview_to_world(world: WorldDefinition, x_px: float, y_px: float) -> tuple[float, float]:
    """Continuous image-edge coordinates to metres (flat) or lon/lat degrees (sphere)."""
    rows, columns = overview_shape(world)
    finite(x_px, "x_px")
    finite(y_px, "y_px")
    valid_y = 0 <= y_px <= rows if world.geometry == "sphere" else 0 <= y_px < rows
    if not 0 <= x_px < columns or not valid_y:
        raise ValueError("selection lies outside the overview")
    if world.geometry == "sphere":
        latitude = 90 - 180 * (y_px / rows)
        longitude = 0.0 if abs(latitude) == 90 else -180 + 360 * (x_px / columns)
        return longitude, latitude
    return world.flat_position(x_px / columns * world.width_m, y_px / rows * world.height_m)


def world_to_overview(world: WorldDefinition, first: float, second: float) -> tuple[float, float]:
    """World position to image-edge coordinates; the south pole lies on the bottom edge."""
    rows, columns = overview_shape(world)
    finite(first, "first coordinate")
    finite(second, "second coordinate")
    if world.geometry == "flat":
        x, y = world.flat_position(first, second)
        return x / world.width_m * columns, y / world.height_m * rows
    if not -90 <= second <= 90:
        raise ValueError("latitude must be in [-90, 90]")
    first = (first + 180) % 360 - 180
    if abs(second) == 90:
        first = 0.0
    return (first + 180) / 360 * columns, (90 - second) / 180 * rows


def overview_scale(world: WorldDefinition, first: float, second: float) -> tuple[float, float]:
    """Metre spans of a pixel at a selected world position, along the projection axes."""
    world_to_overview(world, first, second)
    rows, columns = overview_shape(world)
    if world.geometry == "flat":
        return world.width_m / columns, world.height_m / rows
    cosine = 0.0 if abs(second) == 90 else math.cos(math.radians(second))
    return 2 * math.pi * world.radius_m / columns * cosine, math.pi * world.radius_m / rows


def geography_field(
    world: WorldDefinition,
    first: NDArray[np.float64],
    second: NDArray[np.float64],
    rng: np.random.Generator,
) -> NDArray[np.float64]:
    """Coarse height fractions at world positions; fresh step RNG yields the same field anywhere."""
    first, second = np.broadcast_arrays(
        np.asarray(first, dtype=float), np.asarray(second, dtype=float)
    )
    if not np.isfinite(first).all() or not np.isfinite(second).all():
        raise ValueError("sample coordinates must be finite")
    if world.geometry == "flat":
        if world.boundary == "wrap_x":
            first = first % world.width_m
        if (
            (first < 0).any()
            or (first >= world.width_m).any()
            or (second < 0).any()
            or (second >= world.height_m).any()
        ):
            raise ValueError("sample lies outside the world")
        x, y = first / world.width_m, second / world.height_m
        coordinates = (x, y, np.zeros_like(x))
    else:
        if (abs(second) > 90).any():
            raise ValueError("latitude must be in [-90, 90]")
        longitude = np.deg2rad((first + 180) % 360 - 180)
        latitude = np.deg2rad(second)
        cosine = np.where(abs(second) == 90, 0, np.cos(latitude))
        coordinates = (cosine * np.cos(longitude), cosine * np.sin(longitude), np.sin(latitude))
    frequencies = rng.integers(-2, 3, size=(6, 3))
    phases = rng.uniform(-np.pi, np.pi, size=6)
    noise = np.zeros_like(first)
    for i, (frequency, phase) in enumerate(zip(frequencies, phases, strict=True)):
        angle = sum(f * coordinate for f, coordinate in zip(frequency, coordinates, strict=True))
        noise += 0.5**i * np.cos(2 * np.pi * angle + phase)
    noise /= sum(0.5**i for i in range(6))
    signal = 0.1 + noise
    if world.geometry == "flat":
        # Periodic displacement keeps an island centred across a wrapped world's join.
        dx = (x - 0.5 + 0.5) % 1 - 0.5 if world.boundary == "wrap_x" else x - 0.5
        shape_x = (1 - np.cos(2 * np.pi * x)) / 2 if world.boundary == "wrap_x" else x
        if world.geography == "island":
            signal = 0.65 - 1.2 * np.hypot(2 * dx, 2 * y - 1) + 0.1 * noise
        elif world.geography == "continent":
            signal = 0.6 - 0.85 * abs(2 * shape_x - 0.3) - 0.25 * abs(2 * y - 1) + 0.1 * noise
        elif world.geography == "peninsula":
            signal = 0.6 - 2.5 * abs(2 * y - 1) - 0.9 * shape_x + 0.04 * noise
    else:
        x, y, z = coordinates
        if world.geography in ("island", "continent"):
            radius = 0.65 if world.geography == "island" else 1.3
            signal = radius - np.arccos(np.clip(x, -1, 1)) + 0.1 * noise
        elif world.geography == "peninsula":
            mainland = 0.6 - np.arccos(np.clip(-y, -1, 1))
            tongue = np.minimum(np.minimum(0.16 - abs(z), x), -y - 0.05)
            signal = np.maximum(mainland, tongue) + 0.04 * noise
    datum = (world.sea_level_m - world.height_min_m) / world.height_range_m
    return np.clip(datum + 0.35 * signal, 0, 1)


def generate_overview(world: WorldDefinition) -> NDArray[np.uint16]:
    """Sample only the saved coarse lattice; no erosion or regional detail is implied."""
    rows, columns = overview_shape(world)
    pixels = np.empty((rows, columns), dtype=np.uint16)
    x = (np.arange(columns) + 0.5) / columns
    for start in range(0, rows, ROW_BATCH):
        y = (np.arange(start, min(start + ROW_BATCH, rows)) + 0.5) / rows
        if world.geometry == "flat":
            first, second = x[None, :] * world.width_m, y[:, None] * world.height_m
        else:
            first, second = -180 + 360 * x[None, :], 90 - 180 * y[:, None]
        values = geography_field(world, first, second, step_rng(world.seed, "world.geography"))
        pixels[start : start + len(y)] = np.rint(values * 65535).astype(np.uint16)
    return pixels


def overview_metadata(world: WorldDefinition, pixels: NDArray[np.uint16]) -> dict:
    """Describe the complete lattice and five illustrative reference samples."""
    rows, columns = overview_shape(world)
    if pixels.shape != (rows, columns) or pixels.dtype != np.uint16:
        raise ValueError("overview must be uint16 with the configured shape")
    projection = {"name": "flat" if world.geometry == "flat" else "equirectangular"}
    if world.geometry == "flat":
        projection.update(
            pixel_width_m=world.width_m / columns,
            pixel_height_m=world.height_m / rows,
            units="metres",
            origin=[0, 0],
        )
    else:
        projection.update(
            longitude_step_degrees=360 / columns,
            latitude_step_degrees=180 / rows,
            equatorial_pixel_width_m=2 * math.pi * world.radius_m / columns,
            pixel_height_m=math.pi * world.radius_m / rows,
            units="degrees",
            distortion=("east-west span = equatorial span * cos(latitude); poles collapse"),
        )
    references = []
    for column, row in (
        (0, 0),
        (columns - 1, 0),
        (columns // 2, rows // 2),
        (0, rows - 1),
        (columns - 1, rows - 1),
    ):
        references.append(
            {
                "column": column,
                "row": row,
                "position": overview_to_world(world, column + 0.5, row + 0.5),
                "pixel_span_m": overview_scale(
                    world, *overview_to_world(world, column + 0.5, row + 0.5)
                ),
                "height_uint16": int(pixels[row, column]),
            }
        )
    return {
        "world_id": world.world_id,
        "seed": world.seed,
        "generator_version": world.generator_version,
        "extent": world.extent,
        "geography": world.geography,
        "rows": rows,
        "columns": columns,
        "height_min_m": world.height_min_m,
        "height_range_m": world.height_range_m,
        "sea_level_m": world.sea_level_m,
        "projection": projection,
        "sampling": {
            "rule": "pixel centres at (column+0.5, row+0.5); linear world/projection axes",
            "field": "six-wave-world-geography-v1",
            "step": "world.geography",
            "unresolved_detail": (
                "coastlines between samples and fine terrain are unresolved; "
                "samples are not uniform pixel footprints"
            ),
            "future_detail": "regional refinement must preserve every encoded centre sample",
            "erosion": False,
        },
        "omitted_layers": ["water", "biomes", "settlements", "roads", "borders"],
        "reference_samples": references,
    }
