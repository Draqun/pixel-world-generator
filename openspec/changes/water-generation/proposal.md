# Proposal

## Why

Terrain is implemented, but it has no sea level, lakes or river network. Water is the next
agreed pipeline stage and supplies the constraints needed by biomes and settlement placement.

## What Changes

- Add a recorded sea level, ocean connectivity, depression lakes and connected drainage rivers.
- Export an aligned categorical water PNG without modifying the terrain PNG or R16.
- Record water parameters and layer meanings; extend CLI validation and output determinism tests.
- Keep depression handling distinct from erosion: filled elevations guide drainage, not terrain edits.

## Capabilities

### New Capabilities

- `surface-water`: sea, lakes, drainage rivers and their aligned output layer.

### Modified Capabilities

None. Existing outputs remain present; the water layer is additive.

## Impact

Depends on completed terrain-generation. Extends Params, CLI, metadata, writer and integration
tests; adds pure hydrology functions. No new runtime dependency, game code or simulation of weather.
Original scope and proposed technical choices are distinguished in ../../roadmap.md.
