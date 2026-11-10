"""Command line: `python -m pixel_world generate --seed N`."""

from collections.abc import Sequence
from pathlib import Path

import click
import typer

from pixel_world.params import Params
from pixel_world.terrain import generate_terrain
from pixel_world.water import accumulation, drainage, rivers
from pixel_world.writer import write_world


def generate(params: Params, out: Path) -> None:
    height = generate_terrain(params)
    sea, lake, _, targets = drainage(
        height, params.sea_level, params.height_range_m, params.min_lake_depth_m
    )
    _, water = rivers(
        accumulation(targets), sea, lake, params.river_threshold, params.max_river_width
    )
    write_world(out, height, water, params)


app = typer.Typer(no_args_is_help=True, add_completion=False)
DEFAULT_OUT = Path("out")


def generate_command(
    seed: int = typer.Option(..., "--seed"),
    size: int = typer.Option(Params.size),
    octaves: int = typer.Option(Params.octaves),
    erosion_iterations: int = typer.Option(Params.erosion_iterations),
    island_exponent: float = typer.Option(Params.island_exponent),
    island_warp: float = typer.Option(Params.island_warp),
    erosion_strength: float = typer.Option(Params.erosion_strength),
    erosion_talus: float = typer.Option(Params.erosion_talus),
    height_range: float = typer.Option(Params.height_range_m),
    sea_level: float = typer.Option(Params.sea_level),
    min_lake_depth: float = typer.Option(Params.min_lake_depth_m),
    river_threshold: int = typer.Option(Params.river_threshold),
    max_river_width: int = typer.Option(Params.max_river_width),
    out: Path = DEFAULT_OUT,
) -> None:
    """Generate a terrain heightmap."""
    try:
        params = Params(
            seed=seed,
            size=size,
            octaves=octaves,
            erosion_iterations=erosion_iterations,
            island_exponent=island_exponent,
            island_warp=island_warp,
            erosion_strength=erosion_strength,
            erosion_talus=erosion_talus,
            height_range_m=height_range,
            sea_level=sea_level,
            min_lake_depth_m=min_lake_depth,
            river_threshold=river_threshold,
            max_river_width=max_river_width,
        )
    except ValueError as error:
        raise click.BadParameter(str(error)) from error
    generate(params, out)
    print(f"wrote {out}/ (seed {params.seed}, {params.size}x{params.size})")


app.command("generate")(generate_command)


@app.command()
def interactive() -> None:
    """Configure and preview a world interactively."""
    from pixel_world.interactive import run

    run()


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = app(
            args=list(argv) if argv is not None else None,
            prog_name="pixel_world",
            standalone_mode=False,
        )
    except click.ClickException as error:
        error.show()
        raise SystemExit(error.exit_code) from error
    return result if isinstance(result, int) else 0
