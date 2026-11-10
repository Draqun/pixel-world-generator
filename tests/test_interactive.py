import builtins
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from pixel_world.cli import main
from pixel_world.png import write_png8


def session(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> None:
    values = iter(answers)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(values))
    assert main(["interactive"]) == 0


def test_interactive_requires_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(SystemExit) as exc:
        main(["interactive"])
    assert exc.value.code != 0


def test_generate_then_edit_seed_and_repeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "world"
    session(
        monkeypatch,
        [
            "1",
            "seed",
            "7",
            "size",
            "64",
            "octaves",
            "2",
            "erosion_iterations",
            "1",
            "out",
            str(out),
            "generate",
            "y",
            "seed",
            "8",
            "generate",
            "y",
            "y",
            "back",
            "0",
        ],
    )
    assert json.loads((out / "metadata.json").read_text())["seed"] == 8


def test_decline_overwrite_preserves_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "world"
    out.mkdir()
    (out / "preview.png").write_bytes(b"keep")
    session(monkeypatch, ["1", "seed", "1", "out", str(out), "generate", "y", "n", "back", "0"])
    assert (out / "preview.png").read_bytes() == b"keep"


def test_preview_in_terminal_and_system_viewer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from pixel_world import interactive

    write_png8(tmp_path / "preview.png", np.full((64, 64), 127, dtype=np.uint8))
    opened = []
    monkeypatch.setattr(interactive, "_open_image", lambda path: opened.append(path))
    monkeypatch.setattr(interactive.shutil, "get_terminal_size", lambda: (20, 10))
    session(monkeypatch, ["1", "out", str(tmp_path), "back", "2", "1", "1", "2", "1", "2", "0"])
    assert opened == [tmp_path / "preview.png"]
    assert "Terminal preview" in capsys.readouterr().out


def test_preview_missing_and_viewer_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from pixel_world import interactive

    def fail(_path: Path) -> None:
        raise OSError("no viewer")

    monkeypatch.setattr(interactive, "_open_image", fail)
    write_png8(tmp_path / "preview.png", np.zeros((64, 64), dtype=np.uint8))
    session(monkeypatch, ["1", "out", str(tmp_path), "back", "2", "1", "2", "0"])
    assert "no viewer" in " ".join(capsys.readouterr().out.split())


def test_terminal_preview_fits_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from pixel_world import interactive

    path = tmp_path / "preview.png"
    write_png8(path, np.full((64, 64), 255, dtype=np.uint8))
    monkeypatch.setattr(interactive.shutil, "get_terminal_size", lambda: (10, 8))
    interactive._terminal_preview(path)
    rows = [line for line in capsys.readouterr().out.splitlines() if line == "@" * 10]
    assert len(rows) == 5


def test_missing_images_report_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session(monkeypatch, ["1", "out", str(tmp_path), "back", "2", "0"])
    assert "No preview images" in capsys.readouterr().out


def test_interactive_and_flags_generate_identical_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interactive_out, flags_out = tmp_path / "interactive", tmp_path / "flags"
    session(
        monkeypatch,
        [
            "1",
            "seed",
            "42",
            "size",
            "64",
            "octaves",
            "2",
            "erosion_iterations",
            "1",
            "out",
            str(interactive_out),
            "generate",
            "y",
            "back",
            "0",
        ],
    )
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
                "--out",
                str(flags_out),
            ]
        )
        == 0
    )
    for name in ("heightmap.png", "heightmap.r16", "preview.png", "metadata.json"):
        assert (interactive_out / name).read_bytes() == (flags_out / name).read_bytes()


def test_invalid_values_and_cancellation_write_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "missing"
    session(monkeypatch, ["1", "size", "3", "out", str(out), "generate", "back", "0"])
    assert not out.exists()
