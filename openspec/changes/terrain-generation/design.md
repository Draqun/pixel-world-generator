# Design

## Context

Greenfield Python 3.13 package (`src/pixel_world/`) with `numpy` as the only runtime dependency.
AGENTS.md fixes the binding rules: byte-identical output per seed, one random stream per step,
pure step functions with no I/O, 16-bit heightmap, exact-pinned numerics. See proposal.md for scope.

Maps up to 8192 x 8192 must stay usable, so every step has to be vectorised numpy. A per-pixel
Python loop is not acceptable.

## Goals / Non-Goals

**Goals:**
- A pipeline shape that later slices (water, biomes, ...) can append steps to without touching
  earlier steps.
- Reproducible bytes, not just reproducible shapes.
- 1024 x 1024 generation in seconds, 4096 x 4096 in well under a minute.

**Non-Goals:**
- Physically accurate erosion. The result must look believable, with drainage valleys that the
  water slice can follow, not match a simulation.
- Sea level, rivers or lakes: the heightmap carries no water meaning yet.
- Cross-platform bit-identical floats (AGENTS.md: same platform only).

## Decisions

### Package layout

```
src/pixel_world/
  seeds.py      step_rng(master_seed, step_name) -> numpy.random.Generator
  noise.py      fbm(rng, size, octaves, ...) -> float64 array
  island.py     island_mask(size, ...) -> float64 array in [0, 1]
  erosion.py    erode(height, iterations) -> float64 array
  terrain.py    generate_terrain(params, seed) -> uint16 array   (composes the steps)
  png.py        write_png16 / write_png8 (zlib + struct)
  params.py     Params dataclass: defaults, validation, to_dict
  cli.py        argparse, writes the three files
  __main__.py   python -m pixel_world
```

Step functions take arrays and a `Generator` and return arrays. Only `png.py` and `cli.py` touch
the disk.

### Seed derivation: SHA-256 of the step name into a SeedSequence

`step_rng` builds `SeedSequence(entropy=master_seed, spawn_key=(k,))` where `k` is the first 8
bytes of `sha256(step_name)` as an integer, then `Generator(PCG64(seq))`.
- Stable: depends only on the seed and the name, not on call order or on how many steps ran before.
- Alternative rejected: `SeedSequence.spawn()` in order. It makes a step's stream depend on how many
  streams were spawned before it, which breaks "changing one step does not change another".
- Alternative rejected: Python `hash()`. It is salted per process.

A negative or oversized seed is accepted as any Python int (`SeedSequence` handles big ints);
negative seeds are rejected in validation to avoid ambiguity.

### Noise: own fBm of gradient noise, tiled by octave

Value-noise lattices upscaled bilinearly are cheap but show grid artefacts. Instead, implement 2D
gradient (Perlin-style) noise on a lattice whose random gradients come from the step's `Generator`,
evaluated for all pixels at once with a smoothstep-style fade. fBm sums `octaves` layers with
`lacunarity = 2` and `gain = 0.5`; frequency of the first octave is tied to `size` (not to pixels)
so the same seed gives the same large-scale shape at any `--size`, only with more or less detail.
- Alternative rejected: add `opensimplex`/`noise` dependency. AGENTS.md bans a dependency for a few
  lines, and an external version change would silently change every existing seed.
- Each octave draws its gradients from a sub-stream keyed by the octave number, so adding octaves
  does not change the earlier ones (spec: "octaves add detail, large shape unchanged").

### Island: radial falloff warped by low-frequency noise

`mask = clip(1 - (d / r)^p, 0, 1)`, where `d` is the distance from the centre, `r` reaches the edge,
and `d` is perturbed by a low-frequency noise so the coast is irregular rather than a circle.
Height is `normalise(fbm) * mask`, so the edge is exactly 0 before normalisation. Mask exponent and
warp strength are parameters.
- Alternative rejected: a rectangular falloff (min distance to an edge). It gives square islands.

### Erosion: vectorised grid-based thermal + stream-power pass, not droplet simulation

Droplet erosion (the popular approach) is inherently sequential: millions of Python iterations.
Instead run `iterations` rounds of a vectorised pass over the whole grid:
1. Flow direction: each cell drains to its steepest lower neighbour among 8 (D8), by array shifts.
2. Flow accumulation approximated by a fixed number of relaxation sweeps (cells passing their
   accumulated area downstream), bounded work per iteration.
3. Stream-power incision: `height -= k * accumulation^m * slope` clamped to not go below the
   downstream neighbour.
4. Thermal relaxation: material moves from cells whose slope to a neighbour exceeds a talus angle.

This yields branching valleys that follow drainage, which is exactly what the water slice needs
(rivers will follow the same flow lines). Constants live in `Params` with defaults and are recorded
in metadata. The edge ring is held at its pre-erosion value so the island shape survives.
- Risk: pits created by incision. Mitigated by clamping to the lowest neighbour; real depression
  handling (priority-flood) belongs to the water slice.
- Alternative rejected: `numba`. Heavy dependency, and its compiled float behaviour is another
  determinism variable.

### Fixed numerics

All steps work in `float64`. Quantisation to `uint16` happens once at the end:
`round((h - min) / (max - min) * 65535)`. Operations whose result may depend on summation order
(`sum`, `cumsum` over large arrays) are avoided inside steps or use fixed-order loops.

### Own PNG writer

`png.py` writes PNG with `struct` and `zlib.compress(data, level=9)`. PNG signature, `IHDR`, one
`IDAT`, `IEND`, filter type 0, 16-bit samples big-endian. A fixed compression level and no
ancillary chunks (no timestamp, no software tag) keep the bytes reproducible; a library like Pillow
would add a dependency and its own version-dependent encoder. Tests read the PNG back with the
same module's reader helper (header + IDAT inflate) to check dimensions, bit depth and pixels.

### Metadata JSON

`json.dumps(obj, sort_keys=True, indent=2)` plus a trailing newline. Contents:
`generator_version` (`pixel_world.__version__`, bumped to `0.1.0`), `seed`, and a `params` object
with every field of `Params`. No timestamps.

### CLI

`python -m pixel_world generate --seed N [--size 1024] [--out out/] [--octaves ...]
[--erosion-iterations ...]`. `make generate SEED=42` wraps it. Validation runs in `Params` before
any array is allocated; argparse failures and validation errors exit non-zero without creating the
output directory.

## Risks / Trade-offs

- [Erosion looks wrong or too slow] → Tune on one reference seed and record the timings in the
  README; the tuning constants are parameters, not code.
- [numpy upgrade changes bytes] → numpy is pinned exactly in `pyproject.toml`; the determinism test
  guards each machine, and a golden-hash test for one seed catches silent algorithm changes
  (updating that hash requires bumping `generator_version`).
- [Floats differ across CPUs/BLAS] → out of contract (same platform only); documented in
  AGENTS.md. No BLAS-heavy ops are used.
- [Size 8192 memory] → float64 8192² is 512 MB per array; steps work in place where possible. The
  limit is a parameter bound and can be lowered if it proves too heavy.
