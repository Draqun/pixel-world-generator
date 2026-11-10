# Proposal

## Why

The owner asked to create geographic borders as part of the generated world. This final agreed
stage assigns land to territories while accounting for settlement centres and natural barriers.

## What Changes

- Select territory capitals from generated towns using a recorded territory-count parameter.
- Allocate land with terrain/water-aware growth, keeping sea and inland water unclaimed.
- Export territory IDs, an aligned boundary PNG and JSON territory/capital references.
- Keep terrain, water, biomes, settlements and transport unchanged when border settings change.

## Capabilities

### New Capabilities

- `territory-borders`: deterministic territories, capitals and geographic boundaries.

### Modified Capabilities

None.

## Impact

Implementation follows roads-and-bridges, as required by AGENTS.md. Uses settlement and geography
outputs and bridge traversability; adds pure partitioning functions, layer exports and tests.
No faction lore, diplomacy, changing borders over time or ownership gameplay. The capital rule
and partition cost are proposed technical choices; see ../../roadmap.md.
