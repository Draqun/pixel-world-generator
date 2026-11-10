# Proposal

## Why

The agreed world includes roads between settlements and bridges where routes cross inland water.
Connections must respect slopes and water rather than drawing straight lines through obstacles.

## What Changes

- Route a deterministic settlement network with terrain-aware pathfinding.
- Limit bridge crossings to bounded inland-water spans with valid dry banks.
- Export an aligned roads PNG and JSON paths/bridges referencing settlement IDs.
- Explicitly report unreachable settlements; never create sea crossings or invalid bridges.

## Capabilities

### New Capabilities

- `transport-network`: settlement connections, road paths and bridge entities.

### Modified Capabilities

None.

## Impact

Implementation is blocked until settlement-generation is merged. Adds pathfinding and network
construction, output serialization, CLI parameters and tests. No terrain carving, tunnels, ferries,
street layouts or game scenes. See ../../roadmap.md for source scope and proposed choices.
