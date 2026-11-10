import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from pixel_world.cli import main
from pixel_world.params import Params
from pixel_world.png import read_png

FAST = ["--size", "64", "--octaves", "2", "--erosion-iterations", "2"]
FILES = ("heightmap.png", "heightmap.r16", "preview.png", "metadata.json", "water.png")


def run(out: Path, *args: str) -> int:
    return main(["generate", *args, "--out", str(out)])


def digests(out: Path) -> dict[str, str]:
    return {
        f.name: hashlib.sha256(f.read_bytes()).hexdigest()
        for f in sorted(out.iterdir())
        if f.is_file()
    }


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
    assert meta["seed"] == 7 and meta["generator_version"] == "0.5.0"
    assert meta["sea_level_m"] == 80.0
    assert meta["params"]["sea_level"] == 0.2
    assert meta["params"]["min_lake_depth_m"] == 1.0
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


@pytest.mark.parametrize("seed", ["5", "42"])
def test_same_seed_is_byte_identical(tmp_path: Path, seed: str) -> None:
    run(tmp_path / "a", "--seed", seed, *FAST)
    run(tmp_path / "b", "--seed", seed, *FAST)
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
        ["--seed", "1", "--island-exponent", "nan"],
        ["--seed", "1", "--sea-level", "nan"],
        ["--seed", "1", "--sea-level", "1"],
        ["--seed", "1", "--min-lake-depth", "inf"],
        ["--seed", "1", "--min-lake-depth", "-1"],
        ["--seed", "1", "--river-threshold", "0"],
        ["--seed", "1", "--max-river-width", "0"],
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
    assert digests(tmp_path) == {
        "heightmap.png": "17009a7ac83b5ece48bd626dac9945138249abd045748e9b0edea554eb9fbc72",
        "heightmap.r16": "98664b4d42cdaf1fe5c8f797f1d667ad14ac7c615f2cfe2ee3702a0f78ff245e",
        "preview.png": "3f0dcae62515156d4f1ec45a4eb9e46912f5363315c785851efd6ee8df0fb6c0",
        "water.png": "1d992843364176ede3da84ffc8751bf2277a933d423ef93ac02d20784f4c814d",
        "metadata.json": "f275cb8403a336a18b02633398930b31d131a68a86e3a987f9e08b9865d7cb71",
    }


def test_water_parameters_do_not_change_terrain_files(tmp_path: Path) -> None:
    from pixel_world.cli import generate

    generate(Params(seed=42, size=64, octaves=2, erosion_iterations=2), tmp_path / "a")
    generate(
        Params(
            seed=42, size=64, octaves=2, erosion_iterations=2, sea_level=0.8, min_lake_depth_m=10
        ),
        tmp_path / "b",
    )
    a, b = digests(tmp_path / "a"), digests(tmp_path / "b")
    assert all(
        a[name] == b[name]
        for name in FILES
        if name in ("heightmap.png", "heightmap.r16", "preview.png")
    )
    assert a["metadata.json"] != b["metadata.json"]
    assert a["water.png"] != b["water.png"]


def test_water_layer_and_controls(tmp_path: Path) -> None:
    run(
        tmp_path,
        "--seed",
        "42",
        *FAST,
        "--sea-level",
        "0.4",
        "--min-lake-depth",
        "2",
        "--river-threshold",
        "8",
        "--max-river-width",
        "3",
    )
    water, depth, colour = read_png(tmp_path / "water.png")
    meta = json.loads((tmp_path / "metadata.json").read_text())
    assert water.shape == (64, 64) and (depth, colour) == (8, 0)
    assert set(np.unique(water)) <= {0, 1, 2, 3} and (water == 1).any()
    assert meta["layers"]["water.png"] == {"0": "dry", "1": "sea", "2": "lake", "3": "river"}
    assert meta["sea_level_m"] == 160
    assert [
        meta["params"][k]
        for k in ("sea_level", "min_lake_depth_m", "river_threshold", "max_river_width")
    ] == [0.4, 2, 8, 3]


def test_river_threshold_changes_only_water_and_metadata(tmp_path: Path) -> None:
    run(tmp_path / "a", "--seed", "42", *FAST, "--river-threshold", "1")
    run(tmp_path / "b", "--seed", "42", *FAST, "--river-threshold", "100000")
    a, b = digests(tmp_path / "a"), digests(tmp_path / "b")
    for name in ("heightmap.png", "heightmap.r16", "preview.png"):
        assert a[name] == b[name]
    assert a["water.png"] != b["water.png"]
    assert a["metadata.json"] != b["metadata.json"]


def test_terrain_parameters_are_available_as_flags(tmp_path: Path) -> None:
    assert run(tmp_path, "--seed", "1", *FAST, "--island-warp", "0.5") == 0
    meta = json.loads((tmp_path / "metadata.json").read_text())
    assert meta["params"]["island_warp"] == 0.5
