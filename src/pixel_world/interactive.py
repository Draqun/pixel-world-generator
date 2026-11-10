"""Keyboard and mouse interface for generating and inspecting a world."""

import os
import subprocess
import sys
from pathlib import Path

import click
import numpy as np
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from pixel_world.cli import generate
from pixel_world.params import Params
from pixel_world.png import read_png

FIELDS = {
    "seed": (int, "Seed — non-negative integer; the same seed reproduces the map", None),
    "size": (int, "Map size — width and height in pixels (64–8192, 1 px = 1 m)", Params.size),
    "octaves": (int, "Terrain detail — number of noise layers (at least 1)", Params.octaves),
    "erosion_iterations": (
        int,
        "Erosion passes — more passes take longer (0 or more)",
        Params.erosion_iterations,
    ),
    "island_exponent": (
        float,
        "Island edge falloff — higher values steepen the edge (> 0)",
        Params.island_exponent,
    ),
    "island_warp": (
        float,
        "Island edge distortion — 0 disables warping (0 or more)",
        Params.island_warp,
    ),
    "erosion_strength": (
        float,
        "Erosion strength — 0 disables erosion (0 or more)",
        Params.erosion_strength,
    ),
    "erosion_talus": (
        float,
        "Erosion slope threshold — higher values retain steeper slopes (> 0)",
        Params.erosion_talus,
    ),
    "height_range_m": (float, "Full height range in metres (> 0)", Params.height_range_m),
    "sea_level": (
        float,
        "Sea level — fraction of height range (0 inclusive to 1 exclusive)",
        Params.sea_level,
    ),
    "min_lake_depth_m": (
        float,
        "Minimum lake depth in metres (0 or more)",
        Params.min_lake_depth_m,
    ),
    "river_threshold": (
        int,
        "River threshold — contributing area in square metres (at least 1)",
        Params.river_threshold,
    ),
    "max_river_width": (int, "Maximum river width in pixels (at least 1)", Params.max_river_width),
}
OUTPUTS = ("heightmap.png", "heightmap.r16", "preview.png", "water.png", "metadata.json")


class ConfirmOverwrite(ModalScreen[bool]):
    """Confirm replacing existing generated files."""

    def __init__(self, params: Params, out: Path, overwrite: bool) -> None:
        super().__init__()
        self.summary = f"Seed: {params.seed} | Size: {params.size} × {params.size} | Output: {out}"
        self.warning = (
            "Existing generated files will be overwritten."
            if overwrite
            else "Generate with these settings?"
        )

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm"):
            yield Static(f"{self.summary}\n{self.warning}", id="confirm-message")
            with Horizontal():
                yield Button("Cancel", id="cancel", variant="primary")
                yield Button("Generate", id="overwrite", variant="warning")

    @on(Button.Pressed)
    def choose(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "overwrite")


class WorldApp(App[None]):
    """Edit settings, generate and inspect map layers."""

    CSS = """
    Screen { layout: vertical; }
    #settings { height: 1fr; padding: 0 1; }
    .field { height: 3; }
    .field Label { width: 1fr; padding-top: 1; }
    .field Input { width: 24; }
    #actions { height: 3; padding: 0 1; }
    #status { height: 2; padding: 0 1; }
    #layer { width: 25; }
    #preview { height: auto; max-height: 24; padding: 0 1; }
    ConfirmOverwrite { align: center middle; background: $background 70%; }
    #confirm { width: 54; height: 9; padding: 1 2; background: $surface; border: solid $primary; }
    #confirm-message { height: 3; }
    """
    TITLE = "Pixel World Generator"
    BINDINGS = [("ctrl+q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with VerticalScroll(id="settings"):
            yield Static(
                "Configure a world. Tab moves between fields; edit any value. Seed is required."
            )
            with Horizontal(classes="field"):
                yield Label("Map size preset — choose a starting point or enter a custom size")
                yield Select(
                    [
                        ("Small · 256 m", 256),
                        ("Medium · 512 m", 512),
                        ("Large · 1024 m", 1024),
                        ("Huge · 2048 m", 2048),
                    ],
                    value=1024,
                    allow_blank=False,
                    id="size-preset",
                )
            for name, (_, description, default) in FIELDS.items():
                with Horizontal(classes="field"):
                    yield Label(description)
                    yield Input(
                        value="" if default is None else str(default),
                        placeholder="Required" if default is None else "",
                        id=name,
                    )
            with Horizontal(classes="field"):
                yield Label("Output directory — existing generated files require confirmation")
                yield Input(value="out", id="out")
            yield Static(
                "Preview layer: choose a generated image, then select Preview or Open viewer."
            )
            with Horizontal():
                yield Select(
                    [],
                    prompt="No images found",
                    allow_blank=True,
                    id="layer",
                )
                yield Button("Preview", id="show-preview")
                yield Button("Open viewer", id="open-viewer")
            yield Static("", id="preview")
        yield Static("Ready.", id="status")
        with Horizontal(id="actions"):
            yield Button("Generate world", id="generate", variant="primary")
            yield Button("Quit", id="quit")
        yield Footer()

    @on(Select.Changed, "#size-preset")
    def size_preset(self, event: Select.Changed) -> None:
        if event.value is not Select.BLANK:
            self.query_one("#size", Input).value = str(event.value)

    def message(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    @on(Button.Pressed, "#quit")
    def quit_button(self) -> None:
        self.exit()

    @on(Button.Pressed, "#generate")
    def start_generation(self) -> None:
        try:
            values = {}
            for name, (kind, description, _) in FIELDS.items():
                raw = self.query_one(f"#{name}", Input).value.strip()
                try:
                    values[name] = kind(raw)
                except ValueError as error:
                    raise ValueError(
                        f"{description.split(' — ')[0]} requires a {kind.__name__} value"
                    ) from error
            params = Params(**values)
            out_text = self.query_one("#out", Input).value.strip()
            if not out_text:
                raise ValueError("Output directory is required")
            out = Path(out_text)
        except ValueError as error:
            self.message(f"Invalid settings: {error}. Correct the field and try again.")
            return
        overwrite = any((out / name).exists() for name in OUTPUTS)
        self.push_screen(
            ConfirmOverwrite(params, out, overwrite),
            lambda accepted: self.begin_generation(params, out) if accepted else None,
        )

    def begin_generation(self, params: Params, out: Path) -> None:
        self.query_one("#generate", Button).disabled = True
        self.message("Generating world…")
        self.generate_world(params, out)

    @work(thread=True, exclusive=True)
    def generate_world(self, params: Params, out: Path) -> None:
        try:
            generate(params, out)
        except (OSError, ValueError) as error:
            self.call_from_thread(self.message, f"Generation failed: {error}")
        else:
            self.call_from_thread(self.refresh_layers, out)
            self.call_from_thread(self.message, f"World generated in {out}")
        finally:
            self.call_from_thread(self.enable_generate)

    def enable_generate(self) -> None:
        self.query_one("#generate", Button).disabled = False

    @on(Input.Changed, "#out")
    def output_changed(self, event: Input.Changed) -> None:
        self.refresh_layers(
            Path(event.value.strip()) if event.value.strip() else Path("__missing__")
        )

    def on_mount(self) -> None:
        self.refresh_layers(Path(self.query_one("#out", Input).value))

    def refresh_layers(self, out: Path) -> None:
        names = [
            (label, name)
            for label, name in (
                ("Terrain preview", "preview.png"),
                ("Heightmap", "heightmap.png"),
                ("Water categories", "water.png"),
            )
            if (out / name).is_file()
        ]
        select = self.query_one("#layer", Select)
        select.set_options(names)
        select.value = names[0][1] if names else Select.BLANK

    @on(Button.Pressed, "#show-preview")
    def show_preview(self) -> None:
        path = Path(self.query_one("#out", Input).value.strip()) / str(
            self.query_one("#layer", Select).value
        )
        try:
            pixels, depth, _ = read_png(path)
            rows = min(pixels.shape[0], 20)
            cols = min(pixels.shape[1], max(1, self.size.width - 4), 100)
            sampled = pixels[
                np.linspace(0, pixels.shape[0] - 1, rows, dtype=int)[:, None],
                np.linspace(0, pixels.shape[1] - 1, cols, dtype=int),
            ]
            shades = " .:-=+*#%@"
            if path.name == "water.png":
                shades = " .o#"
                indices = sampled
            else:
                indices = sampled.astype(np.uint32) * (len(shades) - 1) // ((1 << depth) - 1)
            self.query_one("#preview", Static).update(
                "\n".join("".join(shades[int(i)] for i in row) for row in indices)
            )
            self.message(f"Preview: {path}")
        except (OSError, ValueError, IndexError) as error:
            self.message(f"Cannot preview {path}: {error}")

    @on(Button.Pressed, "#open-viewer")
    def open_viewer(self) -> None:
        path = Path(self.query_one("#out", Input).value.strip()) / str(
            self.query_one("#layer", Select).value
        )
        self.launch_viewer(path)

    @work(thread=True, group="viewer")
    def launch_viewer(self, path: Path) -> None:
        try:
            if not path.is_file():
                raise FileNotFoundError(path)
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.run(
                    ["open" if sys.platform == "darwin" else "xdg-open", str(path.resolve())],
                    check=True,
                    capture_output=True,
                )
            self.call_from_thread(self.message, f"Opened {path}")
        except (OSError, subprocess.SubprocessError) as error:
            self.call_from_thread(self.message, f"Cannot open {path}: {error}")


def run() -> None:
    """Run the interactive interface in a terminal."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise click.UsageError("Interactive mode requires a terminal; use generate with flags.")
    WorldApp().run()
