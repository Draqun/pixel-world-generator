# pixel-world-generator

Seeded world map generator. 1 px = 1 m. Python.

Same seed + same generator version = same world.

## Direction and current status

Terrain, water and the interactive terminal interface are implemented. The next planned terrain
milestone is persistent world projects: start with a whole-world overview or only a needed region,
save the project, then generate more areas of the same world without changing existing terrain.
An island is a geography choice; the existing standalone command keeps its island default.
These project/world operations are planned, not available commands yet.

See [the roadmap](openspec/roadmap.md) and
[world project proposal](openspec/changes/planetary-world-regions/proposal.md).
World-linked water requires a separate continuity design before the remaining stages: biomes,
settlements, roads and bridges, then borders. Existing downstream proposals target single maps.

## Usage

```sh
make generate SEED=42 SIZE=256          # writes terrain, water and metadata layers
make generate SEED=42 OUT=out/island42  # SIZE defaults to 1024
make interactive                       # configure and preview with a terminal form
make generate SEED=42 ARGS="--sea-level 0.3 --river-threshold 128"
```

`--seed` is required. `--height-range` (default 400) is how many metres the full 16-bit range
spans; it affects water depths but not terrain pixels. Same seed, generator version and parameters give byte-identical files on the
same platform; `metadata.json` records the seed, generator version and every parameter.
`heightmap.png` is 16-bit grayscale, 1 px = 1 m; `heightmap.r16` holds the same values as a
headerless little-endian uint16 raw file (row-major, top row first), the format Godot terrain addons
import as R16/RAW; `preview.png` is the same image in 8 bits.

`make interactive` opens a keyboard- and mouse-accessible form. Tab moves between fields;
choose a size preset or enter a custom size, enter a seed, and review the explained settings.
Select Generate to review the seed, size and output path before writing; existing generated files
require explicit confirmation before replacement. The layer selector offers existing terrain and
water images for terminal preview or opening in the system viewer. Generation runs in the background.

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

## Water

The water datum defaults to `sea_level=0.2`, a fraction of `height_range_m` in the
range [0, 1). Metadata records `sea_level_m` in metres above the encoded height
minimum; sea-relative elevation is height in metres minus this datum. The default
`min_lake_depth_m=1.0` is a minimum retained depth in metres (non-negative).
`water.png` is an aligned 8-bit grayscale category layer: 0 dry, 1 sea, 2 lake,
3 river. Metadata records this legend and all controls. Set the datum and lake
depth with `--sea-level` and `--min-lake-depth`; set the positive integer river
threshold in square metres and maximum width in pixels with `--river-threshold`
and `--max-river-width`. Pass these options through `ARGS` as shown above.

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

## License

MIT, see `LICENSE`.

## World project foundation

The first world-project slice provides a Python API, persisted definitions and coordinate
conversions. Overview generation, regional terrain exports and their CLI remain planned. The
existing `make generate` and `make interactive` workflows still generate standalone islands.

A project contains:

- `world.json`: the immutable definition and its SHA-256 `world_id`. It records the seed,
  generator/schema/coordinate versions, geometry, metre dimensions or radius, explicit geography,
  vertical minimum/range, absolute sea datum, overview resolution and numeric generation parameters.
  Parameters are persisted configuration; this slice does not interpret them as a terrain algorithm.
- `coverage.json`: separately versioned, canonically ordered completed areas and relative artifact
  paths with SHA-256 hashes. Adding coverage checks completed artifact hashes, preserves existing
  records and atomically replaces only this index. An area's own metadata will locate its bounds
  and projection when regional export is implemented.

Developer API (no raster is required to create or reopen a project):

```python
from pathlib import Path
from pixel_world.world import WorldDefinition
from pixel_world.writer import create_project, load_project

world = WorldDefinition(
    seed=42,
    geometry="flat",
    geography="region",
    width_m=16_000_000,
    height_m=16_000_000,
    boundary="wrap_x",
)
project = create_project(Path("out/story-world"), world)
project = load_project(Path("out/story-world"), expected=world)
position = project.definition.flat_position(-1, 200)  # (15_999_999, 200) metres
```

For a sphere use `geometry="sphere"`, `radius_m=6_000_000`, and leave planar dimensions absent.
The `bounded` boundary field is unused for spheres; spheres have no physical boundary. Flat
worlds accept `bounded` or east-west periodic `wrap_x`; y never wraps. Flat positions are in
half-open `[0, width_m)` and `[0, height_m)` intervals, with origin at top left, x right and y down.
Geography must be explicit (`world`, `region`, `island`, `peninsula` or `continent`); it is recorded
intent until section 2 implements its shaping rules. Project directories must be new. Loading
with incompatible expected settings, unknown versions, incomplete definitions or invalid coverage
fails without writing. Project writes currently require one process per project.

Physical world dimensions, coordinate origin, seed, versions, vertical encoding and geography
are fixed at project creation. Generating further coverage will materialize more of that world,
not stretch its existing terrain or move the origin. Starting with an overview or only a region
will use this same saved definition. A later overview must use the original field and sampling
rules. Caches and in-memory state are disposable. Copies with identical definitions share their
content identity but can be continued independently. Reproduction is guaranteed on the same
platform and supported generator version; unsupported versions require their recorded generator.

### Coordinate convention, version 1

Sphere coordinates use degrees of longitude east and latitude north, with longitude normalized
to `[-180, 180)` and pole longitude canonicalized to zero. Cartesian x points to longitude 0,
y to longitude 90 east, and z north. `pixel_world.coordinates` converts these positions to a
normalized cube-sphere atlas. A face has `u,v` in `[-1,1]`, mapped to the normalized vector
`normal + u * right + v * down`:

| Face | Normal | Right | Down |
| --- | --- | --- | --- |
| +x | (1,0,0) | (0,1,0) | (0,0,-1) |
| -x | (-1,0,0) | (0,-1,0) | (0,0,-1) |
| +y | (0,1,0) | (-1,0,0) | (0,0,-1) |
| -y | (0,-1,0) | (1,0,0) | (0,0,-1) |
| +z | (0,0,1) | (0,1,0) | (1,0,0) |
| -z | (0,0,-1) | (0,1,0) | (-1,0,0) |

The largest absolute Cartesian component selects the face; ties belong to x before y before z
(with absolute tolerance `1e-15` on unit vectors for roundoff). `canonical_cube` gives edges and
corners one owner. Cube face coordinates are dimensionless, not a globally uniform metre grid.
`surface_distance` measures great-circle distances using the recorded sphere radius.

`local_to_lonlat` and `lonlat_to_local` define an azimuthal equidistant local projection with a
fixed world anchor, x east/right, y south/down. Adjacent tiles must share the same anchor and
orientation. At poles the canonical zero-longitude meridian fixes orientation. Radial distances
are exact; at radius `d`, maximum tangential scale excess is `(d/R)/sin(d/R) - 1`. Conversions
reject points exceeding 1% scale excess. An export must check the most distant grid corner and
record the anchor and maximum error; this slice provides conversions, not an export raster.
Global overviews will have a separately recorded projection and resolution.

Run the foundation checks with:

```sh
make test ARGS="tests/test_world.py tests/test_coordinates.py"
make check
```
