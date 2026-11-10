import asyncio
import json
from pathlib import Path

import pytest
from textual.widgets import Input, Select, Static

from pixel_world.interactive import WorldApp


def test_form_explains_settings_and_allows_generation(tmp_path: Path) -> None:
    async def exercise() -> None:
        app = WorldApp()
        async with app.run_test(size=(120, 50)) as pilot:
            assert app.query_one("#seed", Input).placeholder
            assert app.query_one("#size", Input).value == "1024"
            assert app.query_one("#sea_level", Input).value == "0.2"
            app.query_one("#seed", Input).value = "42"
            app.query_one("#size", Input).value = "64"
            app.query_one("#octaves", Input).value = "2"
            app.query_one("#erosion_iterations", Input).value = "1"
            app.query_one("#out", Input).value = str(tmp_path)
            await pilot.click("#generate")
            await pilot.pause()
            await pilot.click("#overwrite")
            await app.workers.wait_for_complete()
            assert json.loads((tmp_path / "metadata.json").read_text())["seed"] == 42
            assert (tmp_path / "water.png").is_file()
            assert app.query_one("#layer", Select).value == "preview.png"

    asyncio.run(exercise())


def test_invalid_and_overwrite_require_confirmation(tmp_path: Path) -> None:
    async def exercise() -> None:
        app = WorldApp()
        async with app.run_test(size=(120, 50)) as pilot:
            app.query_one("#out", Input).value = str(tmp_path)
            await pilot.click("#generate")
            await pilot.pause()
            assert not list(tmp_path.iterdir())
            app.query_one("#seed", Input).value = "1"
            app.query_one("#size", Input).value = "3"
            await pilot.click("#generate")
            await pilot.pause()
            assert not list(tmp_path.iterdir())
            app.query_one("#size", Input).value = "64"
            (tmp_path / "water.png").write_bytes(b"keep")
            await pilot.click("#generate")
            await pilot.pause()
            assert (tmp_path / "water.png").read_bytes() == b"keep"
            assert "overwrite" in str(app.screen.query_one(Static).render()).lower()
            await pilot.click("#cancel")
            assert (tmp_path / "water.png").read_bytes() == b"keep"

    asyncio.run(exercise())


def test_interactive_requires_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    from pixel_world.cli import main

    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(SystemExit):
        main(["interactive"])


def test_existing_output_layer_selection_and_preview(tmp_path: Path) -> None:
    import numpy as np

    from pixel_world.png import write_png8

    write_png8(tmp_path / "water.png", np.ones((8, 8), dtype=np.uint8))

    async def exercise() -> None:
        app = WorldApp()
        async with app.run_test(size=(120, 80)) as pilot:
            app.query_one("#out", Input).value = str(tmp_path)
            await pilot.pause()
            assert app.query_one("#layer", Select).value == "water.png"
            await pilot.click("#show-preview")
            assert "........" in str(app.query_one("#preview", Static).render())

    asyncio.run(exercise())


def test_form_matches_scripted_output(tmp_path: Path) -> None:
    from pixel_world.cli import main

    async def exercise() -> None:
        app = WorldApp()
        async with app.run_test(size=(120, 50)) as pilot:
            for name, value in {
                "seed": "42",
                "size": "64",
                "octaves": "2",
                "erosion_iterations": "1",
                "sea_level": "0.3",
                "out": str(tmp_path / "form"),
            }.items():
                app.query_one(f"#{name}", Input).value = value
            await pilot.click("#generate")
            await pilot.pause()
            await pilot.click("#overwrite")
            await app.workers.wait_for_complete()

    asyncio.run(exercise())
    assert (
        main(
            [
                "generate",
                "--seed",
                "42",
                "--size",
                "64",
                "--octaves",
                "2",
                "--erosion-iterations",
                "1",
                "--sea-level",
                "0.3",
                "--out",
                str(tmp_path / "cli"),
            ]
        )
        == 0
    )
    assert {p.name: p.read_bytes() for p in (tmp_path / "form").iterdir()} == {
        p.name: p.read_bytes() for p in (tmp_path / "cli").iterdir()
    }


def test_viewer_failure_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    import numpy as np

    from pixel_world.png import write_png8

    path = tmp_path / "preview.png"
    write_png8(path, np.zeros((8, 8), dtype=np.uint8))

    def fail(*args: object, **kwargs: object) -> None:
        raise subprocess.CalledProcessError(1, "xdg-open")

    monkeypatch.setattr(subprocess, "run", fail)

    async def exercise() -> None:
        app = WorldApp()
        async with app.run_test(size=(120, 80)) as pilot:
            app.query_one("#out", Input).value = str(tmp_path)
            await pilot.pause()
            await pilot.click("#open-viewer")
            await app.workers.wait_for_complete()
            assert "Cannot open" in str(app.query_one("#status", Static).render())
            assert str(path) in str(app.query_one("#status", Static).render())

    asyncio.run(exercise())
