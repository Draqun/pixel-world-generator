# Design

## Context

Terrain generation returns uint16 heights; CLI currently writes all four outputs itself. Params,
step_rng, grayscale PNG encoding and hash-based integration tests already exist. Erosion has a
private D8 helper and only twelve accumulation sweeps: it is an erosion approximation, not a
complete drainage solution. See proposal.md and ../../roadmap.md for intent and provenance.

## Goals / Non-Goals

**Goals:** coherent catchments, retained lakes and stable layer contracts for the next stage.
**Non-Goals:** modifying terrain beds, groundwater, seasonal simulation or hydrodynamic time steps.

## Decisions

- Proposed module `water.py` takes terrain plus validated controls and returns water classes,
  routing surface, drainage targets and accumulation. No file I/O. Decode metre heights as
  `sample / 65535 * height_range_m` and preserve input arrays.
- Sea is an eight-neighbour flood from below-datum boundary cells, not all below-datum terrain.
  `sea_level` is a normalized fraction in [0, 1), default 0.2; metadata also records derived
  `sea_level_m`. This keeps the existing unsigned height encoding and permits negative
  sea-relative elevations without rewriting heightmap files.
- Use a priority-flood with heapq and fixed row-major tie keys. Seed ocean cells at sea level
  and remaining boundary cells at their ground elevations. Retain original elevations separately;
  lake depth is filled minus original ground outside sea. Default minimum lake depth: 1 m.
- Build acyclic D8 routing by decreasing filled elevation and then flood-visit rank for flats;
  boundary/ocean cells are outlets. Accumulate contributing cell areas exactly in topological
  order. Do not reuse the erosion step's truncated sweeps or alter its private helpers.
- Select rivers at default contributing area 256 square metres. Widen centrelines using a
  bounded accumulation-based radius (default maximum width 9 pixels), preserving categorical
  sea/lake precedence. Width is a map symbol, not an excavated or simulated channel.
- Add water to the existing generate pipeline by default. Move file serialization to one
  `writer.py` when the new output is integrated, preserving existing bytes and CLI entry points;
  do not introduce a plugin pipeline or new dependency. Metadata gains a layer legend and
  the water parameters. Deterministic JSON uses the existing sorted-key/trailing-newline style.
- Extend `make generate` to forward optional ARGS to the existing CLI, so new controls are
  usable through documented Make commands, for example `make generate SEED=42 ARGS="--sea-level 0.2"`.
- Algorithm changes require a generator version bump in both version declarations and deliberate
  golden updates; compute the next version from the branch at implementation time. JSON metadata
  changes are expected; upstream image/raw hashes must remain stable for unchanged terrain inputs.

## Risks / Trade-offs

- [Priority-flood costs time and memory on large grids] → Benchmark 1024 and 2048, report actual
  peak memory and timings; never trade exact drainage for silent sweep truncation. Optimization
  that would change the contract needs a design update before implementation continues.
- [Thresholded tiny depressions become dry routing cells] → Keep drainage independent of the
  display threshold; test flat, bowl, plateau, no-sea and tributary fixtures.
- [Widening can obscure river geometry] → Test centreline connectivity separately from display
  pixels and constrain the width; sea and lake pixels always keep their categories.

## Migration Plan

Land each tasks section in its own PR. Document the additive fifth output before enabling it
in CLI tests. Keep existing four-file compatibility assertions as subset checks and extend
the repeat-run hash test to every emitted file. Rollback reverts the new step and restores the
previous version; existing generated maps remain usable data.
