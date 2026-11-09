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

## License

MIT, see `LICENSE`.
