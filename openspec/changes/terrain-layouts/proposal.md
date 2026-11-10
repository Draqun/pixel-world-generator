# Proposal

## Why

The first owner request described a local land area, island or world. The implemented terrain
always enforces an island, so region and continent-shaped maps need an explicit contract change.

## What Changes

- Add recorded island, region and continent layout selection, retaining island as the default.
- Apply island edge guarantees only to island layout; preserve 16-bit and full-range guarantees.
- Let region terrain reach the map edge and shape a continent as a larger landmass with ocean.
- Verify metre heights and sea-relative depressions using the sea datum introduced by water-generation.

## Capabilities

### New Capabilities

- `terrain-layouts`: explicit layout selection and per-layout geography guarantees.

### Modified Capabilities

- `terrain-heightmap`: scope island-shape requirements to island layout and make erosion preserve
  the selected layout without weakening other formats.

## Impact

An extension after the baseline island pipeline; it does not block water-generation.
Depends on water-generation for the sea-relative interpretation. Extends terrain composition,
Params, CLI and tests; keeps the existing single-map size limits. Large-world tiling is a separate
scope choice. No Godot code or automatic switch to an open-world game. See ../../roadmap.md.
