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

## Terrain (work in progress)

`generate_terrain(Params(seed=42))` builds a 16-bit island heightmap: fractal noise, an island
mask, then grid erosion (stream-power incision along D8 flow plus thermal relaxation). The CLI and
`make generate` arrive in the next slice. Preview of seed 42 at 512 px, 50 erosion iterations:
`docs/terrain-seed42.png`.

Erosion defaults (`erosion_strength=0.04`, `erosion_talus=0.004`, 50 iterations) were tuned by eye
on seed 42. Stronger values (about 0.1) flatten basins into plateaus.

Measured on one machine, seed 42, 50 iterations: 512 px about 2 s, 1024 px 9.6 s, 2048 px 48 s.
Erosion dominates and grows with pixel count, so 4096 px is expected to take minutes.

## License

MIT, see `LICENSE`.
