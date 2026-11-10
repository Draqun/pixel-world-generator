"""Interactive terminal workflow for terrain generation."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import click
import numpy as np
from rich.console import Console
from rich.table import Table

from pixel_world.cli import generate
from pixel_world.params import Params
from pixel_world.png import read_png

FIELDS = {
    "seed": (int, "World seed", "integer >= 0", None),
    "size": (int, "Map width and height in pixels", "64–8192", Params.size),
    "octaves": (int, "Noise detail layers", ">= 1", Params.octaves),
    "erosion_iterations": (int, "Erosion passes", ">= 0", Params.erosion_iterations),
    "island_exponent": (float, "Island edge falloff", "> 0", Params.island_exponent),
    "island_warp": (float, "Island edge distortion", ">= 0", Params.island_warp),
    "erosion_strength": (float, "Erosion strength", ">= 0", Params.erosion_strength),
    "erosion_talus": (float, "Erosion slope threshold", "> 0", Params.erosion_talus),
    "height_range_m": (float, "Height range in metres", "> 0", Params.height_range_m),
    "out": (Path, "Output directory", "path", Path("out")),
}
OUTPUTS = ("heightmap.png", "heightmap.r16", "preview.png", "metadata.json")
console = Console()


def _confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() in ("y", "yes")


def _configure(values: dict) -> None:
    while True:
        table = Table(title="World parameters")
        for heading in ("Name", "Value", "Default", "Description", "Range"):
            table.add_column(heading)
        for name, (_, description, allowed, default) in FIELDS.items():
            table.add_row(name, str(values[name]), str(default), description, allowed)
        console.print(table)
        choice = input("Parameter name, generate, or back: ").strip()
        if choice == "back":
            return
        if choice == "generate":
            if values["seed"] is None:
                console.print("[red]Set a seed first.[/red]")
                continue
            try:
                params = Params(**{k: v for k, v in values.items() if k != "out"})
            except ValueError as error:
                console.print(f"[red]{error}[/red]")
                continue
            if not _confirm("Generate with these values?"):
                continue
            out = values["out"]
            if any((out / name).exists() for name in OUTPUTS) and not _confirm("Overwrite output?"):
                continue
            try:
                generate(params, out)
                console.print(f"Generated world in {out}")
            except OSError as error:
                console.print(f"[red]Could not write {out}: {error}[/red]")
            continue
        if choice not in FIELDS:
            console.print("[red]Choose a listed parameter, generate, or back.[/red]")
            continue
        try:
            candidate = FIELDS[choice][0](input(f"{choice}: ").strip())
            if choice != "out":
                updated = {**values, choice: candidate}
                Params(
                    **{k: v for k, v in updated.items() if k != "out" and v is not None},
                    **({"seed": 0} if updated["seed"] is None else {}),
                )
            values[choice] = candidate
        except ValueError as error:
            console.print(f"[red]Invalid value: {error}[/red]")


def _open_image(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        command = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.run([command, str(path.resolve())], check=True, capture_output=True)


def _terminal_preview(path: Path) -> None:
    pixels, depth, _ = read_png(path)
    width, height = shutil.get_terminal_size()
    rows = max(1, min(pixels.shape[0], height - 3))
    cols = max(1, min(pixels.shape[1], width))
    sampled = pixels[
        np.linspace(0, pixels.shape[0] - 1, rows, dtype=int)[:, None],
        np.linspace(0, pixels.shape[1] - 1, cols, dtype=int),
    ]
    shades = " .:-=+*#%@"
    indices = sampled.astype(np.uint32) * (len(shades) - 1) // ((1 << depth) - 1)
    console.print(f"Terminal preview: {path}")
    for row in indices:
        console.print("".join(shades[int(i)] for i in row), highlight=False, markup=False)


def _preview(out: Path) -> None:
    images = [out / name for name in ("preview.png", "heightmap.png") if (out / name).is_file()]
    if not images:
        console.print(f"No preview images found in {out}")
        return
    for index, path in enumerate(images, 1):
        console.print(f"{index}. {path.name}")
    choice = input("Choose an image (or back): ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(images):
        return
    path = images[int(choice) - 1]
    mode = input("1. Terminal preview  2. System viewer  (or back): ").strip()
    try:
        if mode == "1":
            _terminal_preview(path)
        elif mode == "2":
            _open_image(path)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        console.print(f"[red]Cannot preview {path}: {error}[/red]")


def run() -> None:
    """Run the keyboard-driven menu in an interactive terminal."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise click.UsageError("Interactive mode requires a terminal; use generate with flags.")
    values = {name: spec[3] for name, spec in FIELDS.items()}
    try:
        while True:
            console.print("\n[bold cyan]Pixel World Generator[/bold cyan]")
            console.print("1. Configure and generate\n2. Preview output\n0. Exit")
            choice = input("Choose an action: ").strip()
            if choice == "0":
                return
            if choice == "1":
                _configure(values)
            elif choice == "2":
                _preview(values["out"])
            else:
                console.print("[red]Choose 0, 1 or 2.[/red]")
    except (EOFError, KeyboardInterrupt):
        console.print("\nCancelled.")
