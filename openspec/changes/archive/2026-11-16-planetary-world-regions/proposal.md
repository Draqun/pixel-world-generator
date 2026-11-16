# Proposal

## Why

A metre-scale island-sized image cannot represent a realistically large world or place a story
region in relation to its continents. The owner needs persistent world projects that can start
with either a readable whole-world overview or a detailed local area, then generate additional areas without changing earlier data.
The original island example was not a restriction on the tool.

## What Changes

- Create a world definition and manageable global overview for spherical and flat worlds; allow
  flat worlds to have bounded or horizontally wrapping edges.
- Select a location and materialize only requested metre-scale regions or tiles, aligned with the
  same world, its physical scale and neighbouring regions, without allocating a planet-sized raster.
- Separate geographic extent from terrain shape: a user may start with a world, continent,
  peninsula, island or other regional area; an island is not mandatory.
- Keep the existing single-image generator and its current defaults compatible; use a shared
  world height datum rather than independently normalizing each exported tile.
- Define explicit, honest handling of globally connected water and future layers: no claim that
  independently generated tile edges constitute a complete global drainage or road network.
- Persist all generation-defining project data so region-first projects can resume, generate
  neighbours and produce a later overview of the same world without rewriting existing terrain.
- Make overview creation optional and independent of regional generation.
- Absorb the unimplemented `terrain-layouts` plan here: geography is selected within a world
  project, while the old standalone island command remains compatible.

## Capabilities

### New Capabilities

- `world-geography`: physical-scale world definitions, geometry, overview and geographic choices.
- `regional-materialization`: selection and deterministic, aligned local metre-scale exports.

### Modified Capabilities

- `terrain-heightmap`: scope the existing island and full-range guarantees to legacy standalone
  generation, while allowing world-linked regions to share a height encoding.

## Impact

Affects generation algorithms, coordinate and metadata contracts, exporters, CLI/interface,
fixtures and tests. Requires versioned deterministic world artifacts, a scalable hierarchy and
bounded-memory regional output. Existing PNG/R16 and legacy CLI remain available. Godot rendering,
full-planet metre-resolution files, weather and new downstream game systems are out of scope.
