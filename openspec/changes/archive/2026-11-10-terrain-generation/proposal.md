# Proposal

## Why

`pixel-world-generator` has no generator yet. Terrain is the base of every later slice: water,
biomes, settlements, roads and borders are all computed from the heightmap. The seed contract
("same seed = same world") also has to exist from the first line, because every later step builds
on it and retrofitting determinism is expensive.

## What Changes

- Add a CLI that takes a required `--seed` and produces a world's terrain.
- Generate a heightmap (1 px = 1 m) from fractal noise, shaped into an island by a mask and
  carved by hydraulic erosion.
- Write a 16-bit grayscale PNG heightmap, an 8-bit grayscale PNG preview and a metadata JSON
  (seed, generator version, all parameters).
- Derive one independent random stream per generation step from the master seed.
- Guarantee byte-identical output for the same seed, generator version and parameters, proven by
  a test that generates twice and compares file hashes.
- Add `make generate` and bump the generator version to `0.1.0`.

Out of scope: water bodies (lakes, rivers, sea level), biomes, settlements, roads, bridges, borders,
3D rendering and any Godot integration.

## Capabilities

### New Capabilities

- `seeded-generation`: seed input, per-step random streams, reproducible output, metadata record
  and the command-line entry point.
- `terrain-heightmap`: the heightmap itself (noise, island shape, erosion) and its image outputs.

### Modified Capabilities

None. There are no existing specs.

## Impact

- New code in `src/pixel_world/` and tests in `tests/`.
- New `make generate` target; `README.md` gains usage.
- No new runtime dependency: noise, erosion and the PNG writer are implemented on `numpy`,
  `zlib` and `struct` (per AGENTS.md).
- Output files are generated data under `out/`, which is gitignored.
