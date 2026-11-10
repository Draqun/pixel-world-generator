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
```

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
