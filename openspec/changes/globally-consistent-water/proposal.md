# Proposal

## Why

World-linked terrain exists, but water is deliberately unavailable because independent regional
floods would invent outlets and disagree across exports. Users need an optional world view of
major waterways and more detailed local water, all describing the same persistent world.

## What Changes

- Introduce a versioned, hierarchical world hydrology model: shared ocean connectivity, major
  rivers and lakes, with smaller tributaries and water bodies generated in canonical world cells.
- Offer two overview presentations: terrain only, or terrain with major rivers and large lakes.
  Hiding water changes presentation only; it does not create a different world.
- Materialize smaller water features for detailed regional exports without moving inherited
  waterways, depending on export bounds, or requiring a full-resolution planet raster.
- Record procedural fidelity, physical widths, water surfaces, feature identities and generation
  scales. Do not advertise exact global metre-scale catchments or discharge simulation.
- Add hydrology-conditioned terrain for explicitly enabled new worlds so prescribed waterways
  have actual channels and basins. Presentation controls never change terrain.
- **BREAKING, opt-in model:** hydrology-enabled worlds use a new definition/schema and generator
  version. Existing projects are not silently upgraded or given water over incompatible terrain;
  unsupported recorded versions fail before writes. Legacy standalone water remains unchanged.
- Deliver five implementation slices, with reference maps and continuity/resource checks before
  downstream biome work. No implementation is part of this proposal.

## Capabilities

### New Capabilities

- `world-hydrology`: Immutable multiscale water geography, bounded canonical refinement,
  terrain conditioning, presentation and fidelity contracts.

### Modified Capabilities

- `surface-water`: Scope existing boundary-seeded and terrain-preservation rules to legacy
  standalone maps; world-linked water follows the distinct world-hydrology contract.
- `world-geography`: Support water-free and major-water overview variants of one world.
- `output-documentation`: Explain available world water, hidden detail and approximation instead
  of unconditionally declaring world-linked water absent.

## Impact

Reuse world definitions/identity in `world.py`, coordinate ownership in `coordinates.py`,
`geography_field` and overview sampling in `overview.py`, regional terrain/erosion in `regional.py`,
seed streams in `seeds.py`, PNG encoding and transactional publication in `writer.py`.
Add pure hydrology generation code; extend `world_cli.py` and existing Make workflows, metadata,
output guides, reference scripts and focused tests. No numerical dependency is added. The
standalone interactive application keeps its existing workflow. Both roadmaps track this change;
existing downstream proposals still need reconciliation for world-linked use.
