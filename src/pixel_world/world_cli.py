"""Project lifecycle, overview selection and regional export commands."""

import json
import math
from dataclasses import asdict
from pathlib import Path

import click
import typer

from pixel_world.coordinates import lonlat_to_local
from pixel_world.overview import (
    generate_overview,
    overview_scale,
    overview_shape,
    overview_to_world,
)
from pixel_world.regional import Region, region_context, regional_controls
from pixel_world.world import WorldDefinition
from pixel_world.writer import create_project, load_project, write_overview, write_region

PROJECT_OPTION = typer.Option(..., "--project")


def world_create(
    project: Path = PROJECT_OPTION,
    seed: int = typer.Option(..., "--seed"),
    geometry: str = typer.Option(..., "--geometry", help="flat or sphere"),
    geography: str = typer.Option(
        ..., "--geography", help="region, world, island, peninsula or continent"
    ),
    extent: str = "world",
    width_m: float | None = None,
    height_m: float | None = None,
    radius_m: float | None = None,
    boundary: str = "bounded",
    height_min_m: float = 0.0,
    height_range_m: float = 400.0,
    sea_level_m: float = 80.0,
    overview_resolution: int = 512,
    detail_amplitude_m: float = 8.0,
    erosion_iterations: int = 0,
    erosion_strength: float = 0.02,
    erosion_talus: float = 0.01,
) -> None:
    """Create a new saved world definition without generating any rasters."""
    try:
        definition = WorldDefinition(
            seed=seed,
            geometry=geometry,
            geography=geography,
            extent=extent,
            width_m=width_m,
            height_m=height_m,
            radius_m=radius_m,
            boundary=boundary,
            height_min_m=height_min_m,
            height_range_m=height_range_m,
            sea_level_m=sea_level_m,
            overview_resolution=overview_resolution,
            parameters=(
                ("detail_amplitude_m", detail_amplitude_m),
                ("erosion_iterations", erosion_iterations),
                ("erosion_strength", erosion_strength),
                ("erosion_talus", erosion_talus),
            ),
        )
        regional_controls(definition)
        overview_shape(definition)
        create_project(project, definition)
    except (ValueError, OSError) as error:
        raise click.BadParameter(str(error)) from error
    typer.echo(
        json.dumps({"project": str(project), "world_id": definition.world_id}, sort_keys=True)
    )


def world_info(project: Path = PROJECT_OPTION) -> None:
    """Resume a saved project and print its definition and completed coverage as JSON."""
    try:
        state = load_project(project)
    except (ValueError, OSError) as error:
        raise click.BadParameter(str(error)) from error
    typer.echo(
        json.dumps(
            {
                "world_id": state.definition.world_id,
                "definition": state.definition.to_dict(),
                "coverage": [asdict(record) for record in state.coverage],
            },
            sort_keys=True,
        )
    )


def world_overview(project: Path = PROJECT_OPTION) -> None:
    """Add a coarse overview to a saved project, preserving existing regional exports."""
    try:
        world = load_project(project).definition
        write_overview(project, world, generate_overview(world))
    except (ValueError, OSError) as error:
        raise click.BadParameter(str(error)) from error
    typer.echo(
        json.dumps(
            {"directory": str(project / "overview"), "world_id": world.world_id}, sort_keys=True
        )
    )


def world_select(
    project: Path = PROJECT_OPTION,
    overview_x: float = typer.Option(
        ..., "--overview-x", help="Continuous image-edge pixel coordinate"
    ),
    overview_y: float = typer.Option(
        ..., "--overview-y", help="Continuous image-edge pixel coordinate"
    ),
    width: int = 512,
    height: int = 512,
    anchor_lon: float | None = None,
    anchor_lat: float | None = None,
) -> None:
    """Return a validated metre grid centred near an overview selection; no image is required."""
    try:
        world = load_project(project).definition
        first, second = overview_to_world(world, overview_x, overview_y)
        # Validate dimensions and paired anchor before arithmetic or coordinate conversion.
        grid = Region(0, 0, width, height, anchor_lon=anchor_lon, anchor_lat=anchor_lat)
        if world.geometry == "sphere":
            if anchor_lon is None:
                grid = Region(0, 0, width, height, anchor_lon=first, anchor_lat=second)
            x, y = lonlat_to_local(grid.anchor_lon, grid.anchor_lat, first, second, world.radius_m)
        else:
            x, y = first, second
        grid = Region(
            math.floor(x - width / 2),
            math.floor(y - height / 2),
            width,
            height,
            anchor_lon=grid.anchor_lon,
            anchor_lat=grid.anchor_lat,
        )
        _, scale_error = region_context(world, grid)
        span = overview_scale(world, first, second)
    except (ValueError, OSError) as error:
        raise click.BadParameter(str(error)) from error
    typer.echo(
        json.dumps(
            {
                "world_id": world.world_id,
                "position": [first, second],
                "position_units": "metres" if world.geometry == "flat" else "degrees",
                "pixel_span_m": span,
                "grid": asdict(grid),
                "max_scale_error": scale_error,
            },
            sort_keys=True,
        )
    )


def region_export(
    project: Path = PROJECT_OPTION,
    x: int = typer.Option(..., "--x", help="Left grid edge in metres"),
    y: int = typer.Option(..., "--y", help="Top grid edge in metres"),
    width: int = 512,
    height: int = 512,
    anchor_lon: float | None = None,
    anchor_lat: float | None = None,
    water: str = typer.Option(
        "none", help="Only none is available; world-linked drainage is unavailable"
    ),
) -> None:
    """Export terrain on a saved world's fixed grid, without generating regional water."""
    try:
        world = load_project(project).definition
        grid = Region(x, y, width, height, anchor_lon=anchor_lon, anchor_lat=anchor_lat)
        directory = write_region(project, world, grid, water=water)
    except (ValueError, OSError) as error:
        raise click.BadParameter(str(error)) from error
    typer.echo(
        json.dumps({"directory": str(directory), "world_id": world.world_id}, sort_keys=True)
    )
