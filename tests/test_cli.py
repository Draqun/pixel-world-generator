import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from pixel_world.cli import main
from pixel_world.params import Params
from pixel_world.png import read_png

FAST = ["--size", "64", "--octaves", "2", "--erosion-iterations", "2"]
FILES = ("heightmap.png", "heightmap.r16", "preview.png", "metadata.json")


def run(out: Path, *args: str) -> int:
    return main(["generate", *args, "--out", str(out)])


def digests(out: Path) -> dict[str, str]:
    return {f: hashlib.sha256((out / f).read_bytes()).hexdigest() for f in FILES}


def test_writes_files_and_creates_directory(tmp_path: Path) -> None:
    out = tmp_path / "missing" / "dir"
    assert run(out, "--seed", "1", *FAST) == 0
    assert all((out / f).is_file() for f in FILES)


def test_heightmap_and_preview_format(tmp_path: Path) -> None:
    run(tmp_path, "--seed", "1", "--size", "128", "--octaves", "2", "--erosion-iterations", "2")
    height, depth, colour = read_png(tmp_path / "heightmap.png")
    preview, pdepth, _ = read_png(tmp_path / "preview.png")
    assert height.shape == (128, 128) and (depth, colour) == (16, 0)
    assert height.min() == 0 and height.max() == 65535
    assert pdepth == 8 and preview.shape == height.shape
    assert np.array_equal(preview, np.round(height / 257).astype(np.uint8))


def test_default_size_is_1024() -> None:
    assert Params(seed=1).size == 1024


def test_metadata_records_run_including_defaults(tmp_path: Path) -> None:
    run(tmp_path, "--seed", "7", "--octaves", "3", "--size", "64", "--erosion-iterations", "1")
    meta = json.loads((tmp_path / "metadata.json").read_text())
    assert meta["seed"] == 7 and meta["generator_version"] == "0.1.0"
    assert meta["params"]["octaves"] == 3
    assert {
        "island_exponent",
        "island_warp",
        "erosion_strength",
        "erosion_talus",
        "height_range_m",
    } <= set(meta["params"])


def test_raw_file_matches_png(tmp_path: Path) -> None:
    run(tmp_path, "--seed", "3", "--size", "96", "--octaves", "2", "--erosion-iterations", "2")
    height = read_png(tmp_path / "heightmap.png")[0]
    raw = (tmp_path / "heightmap.r16").read_bytes()
    assert len(raw) == 96 * 96 * 2
    assert np.array_equal(np.frombuffer(raw, dtype="<u2").reshape(96, 96), height)


def test_height_range_recorded_and_pixels_unchanged(tmp_path: Path) -> None:
    run(tmp_path / "a", "--seed", "4", *FAST)
    run(tmp_path / "b", "--seed", "4", *FAST, "--height-range", "800")
    meta = json.loads((tmp_path / "b" / "metadata.json").read_text())
    assert meta["params"]["height_range_m"] == 800
    a, b = digests(tmp_path / "a"), digests(tmp_path / "b")
    assert a["heightmap.png"] == b["heightmap.png"] and a["heightmap.r16"] == b["heightmap.r16"]
    assert a["metadata.json"] != b["metadata.json"]


def test_same_seed_is_byte_identical(tmp_path: Path) -> None:
    run(tmp_path / "a", "--seed", "5", *FAST)
    run(tmp_path / "b", "--seed", "5", *FAST)
    assert digests(tmp_path / "a") == digests(tmp_path / "b")


def test_different_seeds_differ(tmp_path: Path) -> None:
    run(tmp_path / "a", "--seed", "1", *FAST)
    run(tmp_path / "b", "--seed", "2", *FAST)
    assert digests(tmp_path / "a")["heightmap.png"] != digests(tmp_path / "b")["heightmap.png"]


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--seed", "abc"],
        ["--seed", "-3"],
        ["--seed", "1", "--size", "63"],
        ["--seed", "1", "--size", "8193"],
        ["--seed", "1", "--height-range", "0"],
        ["--seed", "1", "--height-range", "-1"],
    ],
)
def test_bad_input_exits_nonzero_and_writes_nothing(tmp_path: Path, args: list[str]) -> None:
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as exc:
        run(out, *args)
    assert exc.value.code != 0
    assert not out.exists()


def test_golden_hash_seed_42(tmp_path: Path) -> None:
    # Update only together with a generator_version bump (algorithm change).
    # Same-platform contract: zlib and numpy are not pinned across machines.
    run(tmp_path, "--seed", "42", "--size", "128")
    assert (
        digests(tmp_path)["heightmap.png"]
        == "17009a7ac83b5ece48bd626dac9945138249abd045748e9b0edea554eb9fbc72"
    )
