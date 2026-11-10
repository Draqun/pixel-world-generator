# pixel-world-generator

Seeded world map generator. 1 px = 1 m. Python.

Same seed + same generator version = same world.

## Planned slices

1. Skeleton, `--seed`, terrain (16-bit heightmap, island mask, erosion), PNG preview
2. Water: lakes, rivers, sea
3. Biomes and masks
4. Settlements (towns, villages, fortresses) as JSON
5. Roads and bridges
6. Borders

## Usage

```sh
make generate SEED=42 SIZE=256          # writes out/heightmap.png, preview.png, metadata.json
make generate SEED=42 OUT=out/island42  # SIZE defaults to 1024
make generate SEED=42 SIZE=256 ARGS="--island-warp 0.5 --erosion-iterations 5"
make interactive                       # edit parameters and preview a world
```

`make interactive` opens a keyboard menu. Choose a parameter by name, enter its value, then
select `generate`; settings remain available for another run. Existing output requires
confirmation before replacement. Preview an image in the terminal or open the system image viewer;
terminal previews are scaled and use monochrome characters. The terminal and viewer must be
available on the host. For scripts, `make generate` never prompts; pass extra flags through
`ARGS`, and use `make generate SEED=42 ARGS=--help` to list them.

`--seed` is required. `--height-range` (default 400) is how many metres the full 16-bit range
spans; it is only recorded in `metadata.json` and does not change any pixel. Same seed, generator version and parameters give byte-identical files on the
same platform; `metadata.json` records the seed, generator version and every parameter.
`heightmap.png` is 16-bit grayscale, 1 px = 1 m; `heightmap.r16` holds the same values as a
headerless little-endian uint16 raw file (row-major, top row first), the format Godot terrain addons
import as R16/RAW; `preview.png` is the same image in 8 bits.

## Terrain

Fractal noise, an island mask, then grid erosion (stream-power incision along D8 flow plus thermal
relaxation). Preview of seed 42 at 512 px, 50 erosion iterations: `docs/terrain-seed42.png`.

Erosion defaults (`erosion_strength=0.04`, `erosion_talus=0.004`, 50 iterations) were tuned by eye
on seed 42. Stronger values (about 0.1) flatten basins into plateaus.

Measured on one machine, seed 42, 50 iterations: 512 px about 2 s, 1024 px 9.6 s, 2048 px 48 s.
Erosion dominates and grows with pixel count, so 4096 px is expected to take minutes.

## Changelog and releases

Every PR adds an English Markdown fragment in `changelog.d/`: `<issue>.added.md`,
`<issue>.changed.md`, `<issue>.fixed.md` or `<issue>.removed.md`. Without an issue use a unique
name such as `+release-automation.added.md`. Do not edit generated changelog entries by hand.

```sh
make changelog-draft                       # preview only
make changelog-check TARGET_BRANCH=main    # compare against origin/main
make release-check                        # validate local release prerequisites
make build                                # wheel and sdist in dist/
```

Fetch the target branch before checking fragments. The `Checks and changelog` Actions job runs
`make check` and checks fragments against the actual PR base, including stacked PRs. Configure
it as a required check in branch protection if merges must be blocked on failure.

To release, first merge the intended version in both `pyproject.toml` and
`src/pixel_world/__init__.py` (format `X.Y.Z`). Algorithm changes require a generator version
bump. In GitHub Actions, manually run **Release** on **main**. The workflow runs checks, consumes
fragments into `CHANGELOG.md`, commits that change, atomically pushes main and tag `vX.Y.Z`, and
creates a GitHub Release with wheel and sdist attachments. Existing tags are never overwritten.
Nothing is published to PyPI. Local changelog assembly is `make changelog-build`.

The workflow uses the built-in `GITHUB_TOKEN` with `contents: write`; repository rules must
permit its release commit on main. No additional secret is needed. A concurrent update to main
causes publication to fail without overwriting the newer commit.

If the commit and tag were pushed but GitHub Release creation failed, keep the tag. Check out
that tag in a clean checkout, rebuild with `make build`, copy its changelog section to a notes
file, and finish the release (replace the example version):

```sh
gh release create v0.1.0 dist/* --verify-tag --title v0.1.0 --notes-file release-notes.md
```

If the release already exists but an upload failed, attach the missing files with
`gh release upload v0.1.0 dist/*` instead. Do not rerun the full workflow or move the tag.

## License

MIT, see `LICENSE`.

The water datum defaults to `sea_level=0.2`, a fraction of `height_range_m` in the
range [0, 1). Metadata records `sea_level_m` in metres above the encoded height
minimum; sea-relative elevation is height in metres minus this datum. The default
`min_lake_depth_m=1.0` is a minimum retained depth in metres (non-negative).
These parameters are recorded now; the water layer and CLI controls follow in a later slice.

River centrelines start at a contributing area of 256 m² by default. Each cell
counts itself and all upstream cells exactly. The display widens channels in
steps based on the base-2 logarithm of area divided by the threshold, capped by
`max_river_width` (default 9 pixels). This is a map symbol, not an excavated bed
or a hydraulic simulation. Sea and lakes take precedence over the symbol.

Run `make water-benchmark` to measure seed 42 at 1024 and 2048 and write
`out/water-preview-1024.png` and `out/water-preview-2048.png`. These diagnostic
images show sea in dark grey, lakes in light grey and rivers in white over the
terrain. Reference run on Linux x86-64, Intel i7-13800H, Python 3.13.8 and
NumPy 2.3.3, default parameters (peak RSS covers the complete process):

| Size | Terrain | Water | Peak RSS |
| --- | ---: | ---: | ---: |
| 1024 | 11.65 s | 6.13 s | 131.0 MiB |
| 2048 | 52.81 s | 24.38 s | 398.7 MiB |
