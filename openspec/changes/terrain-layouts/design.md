# Design

## Context

Current base_height always multiplies normalized noise by island_mask, and erosion holds whatever
edge ring it receives. The main terrain spec unconditionally promises an island; its erosion
scenarios also mention island shape. Water-generation introduces the separate sea datum.

## Goals / Non-Goals

**Goals:** expand the original area/island/world idea with explicit layouts and preserve formats.
**Non-Goals:** tiling, infinite terrain, wraparound planets or an open-world game integration.

## Decisions

- Add `layout` to Params/CLI with island default. Keep the existing island path's formulas and
  random step names unchanged, so default and explicit-island terrain remain pixel-identical.
- Region bypasses only the island falloff. Continent uses an offset, broad, low-frequency land
  envelope that reaches one boundary while leaving ocean on another under reference parameters.
  Use its own `terrain.layout` stream so shape choices never perturb existing noise draws.
- Apply erosion to each composed layout. Its existing fixed edge ring preserves region/continent
  boundary values; do not force those edges to zero. Quantize once over the entire single map,
  as today; continue using the same writer and unsigned height range.
- Modify both Island shape and Hydraulic erosion requirements: preserve existing scenario names
  and scope shape promises to the selected layout. Do not silently weaken full-range, PNG/R16,
  metre-coordinate or preview requirements.
- Depressions mean negative elevation relative to the separate recorded sea datum, not negative
  uint16 samples. Ocean classification still requires boundary connectivity; a local enclosed
  depression is not automatically sea. Test this with the merged water-stage fixtures.
- Implement after the baseline island pipeline, with water-generation as the minimum technical
  prerequisite. Later layers consume the new geography without changing their algorithms.
  Bump generator version and update metadata/goldens deliberately; preserve terrain samples for
  the existing island path and document this narrower compatibility guarantee.

## Risks / Trade-offs

- [A continent preset does not guarantee any desired coastline for every sea setting] → Guarantee
  the documented reference case, not every arbitrary threshold; keep the selected controls recorded.
- [Changing layout legitimately changes every geographic result] → Test independent streams with
  identical array inputs rather than claiming downstream outputs should ignore their geography.
- [The word world suggests unlimited size] → This change explicitly retains current size limits;
  large-world export is separate, not a hidden relaxation of the 8192 bound.

## Migration Plan

First add layout composition and scoped terrain contracts, then integrate CLI/full-pipeline
examples in a second PR. Keep island default throughout and do not alter the consumer repository.
