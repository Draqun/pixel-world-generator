# Tasks

## 1. Seeds, parameters and PNG writer

- [ ] 1.1 Add `seeds.py` with `step_rng(master_seed, step_name)`; verify tests: same inputs give the same sequence, different step names give different sequences, call order does not matter
- [ ] 1.2 Add `params.py` (`Params` dataclass with defaults, validation: seed int >= 0, size 64..8192, octaves >= 1, erosion iterations >= 0, `to_dict`); verify tests cover every rejected value and the default size 1024
- [ ] 1.3 Add `png.py` (`write_png16`, `write_png8`, and a small reader used by tests); verify a round-trip test returns identical pixels, header reports colour type 0 and the right bit depth, and two writes of the same array are byte-identical

## 2. Noise and island shape

- [ ] 2.1 Add `noise.py` with `fbm` (gradient noise, per-octave sub-streams, large-scale shape tied to `size`); verify tests: deterministic, adding octaves keeps the large-scale shape (low-pass of 4-octave and 6-octave output correlate above 0.99), output range is finite
- [ ] 2.2 Add `island.py` with `island_mask` (radial falloff warped by low-frequency noise); verify tests: mask is 0 on the edge, 1 near the centre, values within [0, 1]
- [ ] 2.3 Add `terrain.py` composing noise and mask with erosion off, quantised to `uint16` in [0, 65535]; verify tests for spec scenarios "Range", "Edge is low" and "Interior is higher"

## 3. Erosion

- [ ] 3.1 Add `erosion.py` (D8 flow, bounded accumulation sweeps, stream-power incision clamped to the lowest neighbour, thermal relaxation, edge ring held); verify unit tests on tiny hand-made grids (a tilted plane, a single peak, a pit)
- [ ] 3.2 Wire erosion into `terrain.py` behind `erosion_iterations` (0 disables); verify tests: 0 iterations equals the un-eroded terrain, a positive count changes it and keeps the range and island-shape scenarios true, changing erosion parameters leaves the pre-erosion noise field identical
- [ ] 3.3 Tune default erosion constants on seed 42 at size 1024 and record the resulting timing and a preview image path in `README.md`; verify by running `make generate SEED=42` after section 4 and looking at `preview.png` (valleys branch downhill, no grid artefacts)

## 4. CLI, outputs and determinism

- [ ] 4.1 Add `cli.py`, `__main__.py` and a `generate` subcommand writing `heightmap.png`, `preview.png`, `metadata.json` (`sort_keys`, trailing newline, no timestamps); verify tests for spec scenarios "Default files", "Directory missing", "Metadata contents", "Preview matches heightmap"
- [ ] 4.2 Reject a missing or non-integer seed and out-of-range size before any output exists; verify tests assert non-zero exit status and that the output directory was not created
- [ ] 4.3 Add the determinism test (generate twice into two directories, compare SHA-256 of all three files; two seeds differ) and a golden-hash test for seed 42 at size 128; verify both pass under `make test`
- [ ] 4.4 Bump `__version__` to `0.1.0`, add `make generate` (`SEED`, `SIZE`, `OUT` variables) and document usage, outputs and the determinism contract in `README.md`; verify `make generate SEED=42 SIZE=256` produces the three files and `make check` passes

## Workflow follow-up

- Each section above is one PR (`Part of` the tracking issue). Archive the change in the last PR, after the owner confirmed the preview looks right.
