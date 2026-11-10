# Design

## Context

Implementation depends on water-generation's categorical water and freshwater masks. The current
writer supports grayscale uint8/uint16 and Params carries metre height range. No biome or distance
helper exists. The new stage must not recalculate or edit upstream terrain/water. See proposal.md.

## Goals / Non-Goals

**Goals:** readable categories and unit-defined environmental masks, suitable for later scoring.
**Non-Goals:** weather, latitude, vegetation objects, texture painting or biological simulation.

## Decisions

- Proposed `biomes.py` receives metre terrain and water arrays and its own Generator from
  `step_rng(seed, "biomes.moisture")`. Return float slope/moisture and uint8 biome IDs without I/O.
- Derive slope from finite differences in metre heights at one-metre spacing; use one-sided
  derivatives at the edge. Convert gradient magnitude with arctangent. Do not wrap array edges.
- Compute distance to lake/river cells with an eight-neighbour multi-source shortest-path pass,
  explicitly using octile rather than exact Euclidean distance. Reuse this helper for freshwater
  access in settlements. With no freshwater, the distance contribution is zero moisture.
- Moisture is `clip(0.7 * exp(-distance / 128m) + 0.3 * noise, 0, 1)`, with deterministic
  low-frequency noise from the existing noise primitives and this stage's stream. Sea is not
  freshwater. The distance scale and mixture are recorded controls, not recovered owner choices.
- Encode IDs: 0 water, 1 grassland, 2 forest, 3 wetland, 4 rock, 5 snow. Apply precedence:
  water; rock at slope >= 40 degrees; snow at normalized height >= 0.8; wetland below height
  0.35 with moisture >= 0.7 and slope <= 10 degrees; forest at moisture >= 0.5; else grassland.
  Record these proposed defaults and the layer legends. Threshold tests cover equality.
- Export `slope.png = round(angle / 90 * 255)`, `moisture.png = round(moisture * 255)` and
  `biome.png` through the writer introduced by water-generation. In-memory consumers use
  unquantized fields. Add finite/bounds validation to Params and relevant CLI flags; no new library.
- Bump the current generator version and update golden outputs intentionally. Test all-file
  repeat hashes and biome-parameter isolation of the already merged water/terrain outputs.

## Risks / Trade-offs

- [Moisture is an artistic proxy] → Name it as such and document deterministic reference previews;
  do not claim climate realism. Tuning changes are parameters recorded in metadata.
- [Distance transform is expensive] → Benchmark the default map and retain only needed arrays;
  do not add SciPy to avoid implementing this one helper.
- [Height range changes physical slope] → Test a known metre ramp and explicitly record units;
  normalized altitude thresholds remain separate from metre slope.

## Migration Plan

Wait for water-generation, then implement one tasks section per PR. Additive masks do not replace
the heightmap preview. Rollback removes this stage and its output declarations, leaving source
terrain and water data intact.
