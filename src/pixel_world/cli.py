"""Command line: `python -m pixel_world generate --seed N`."""

import json
from collections.abc import Sequence
from pathlib import Path

import click
import numpy as np
import typer

from pixel_world import __version__
from pixel_world.params import Params
from pixel_world.png import write_png8, write_png16
from pixel_world.terrain import generate_terrain


def _metadata(params: Params) -> str:
    fields = params.to_dict()
    meta = {
        "generator_version": __version__,
        "seed": fields.pop("seed"),
        "params": fields,
        "sea_level_m": params.sea_level * params.height_range_m,
    }
    return json.dumps(meta, sort_keys=True, indent=2) + "\n"


def generate(params: Params, out: Path) -> None:
    height = generate_terrain(params)
    preview = ((height.astype(np.uint32) + 128) // 257).astype(np.uint8)  # round(h / 257)
    out.mkdir(parents=True, exist_ok=True)
    write_png16(out / "heightmap.png", height)
    (out / "heightmap.r16").write_bytes(height.astype("<u2").tobytes())
    write_png8(out / "preview.png", preview)
    (out / "metadata.json").write_text(_metadata(params), encoding="utf-8")


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
    return 0
