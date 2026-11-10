# World generation roadmap and recovered decisions

This is a planning index, not evidence that pending features are implemented. Current main specs
cover seeded terrain and release management. Every pending change has proposal, specs, design
and tasks; implementation requires a separate apply request. Each tasks section is one PR.

## Sources and confidence

The original Claude Code session, from 2026-11-09, is `b34aa740-ccd2-4d57-a50e-871894765f14`, stored locally under
`~/selflearning/.claude-personal/projects/-home-damian-selflearning-pixel-world-generator/`.
Only the relevant user/assistant text was used; tool transcripts and unrelated game lore are not
requirements. Local JSONL line references below identify the source messages.

| Source | Recovered content | Treatment |
| --- | --- | --- |
| Owner, line 10 | One pixel per metre; local area, island or world; depressions through mountains; water, towns, villages, bridges, fortresses and borders | Product scope |
| Owner, line 42 | Generator must accept a seed | Binding, already implemented |
| Owner, lines 55 and 64 | Python is acceptable; a separate generator tool | Binding project boundary |
| Claude, lines 33 and 58 | Terrain, water, biomes, settlements, roads/bridges, borders; proposed algorithms and staged delivery | Stage order adopted in AGENTS.md; algorithms remain design proposals |
| Owner, lines 838 and 848 | Engine-readable output; add R16 and metre height range | Already implemented; do not rewrite as pending work |
| Current AGENTS.md | Independent streams, pure generation steps, versioned deterministic bytes, PNG layers and JSON, one tasks section per PR | Binding implementation constraints |
| Current README.md | Remaining baseline stage order | Baseline implementation sequence |

The original discussion did not decide an open-world game, city interiors, factions, names,
weather, ferries, tunnels or engine integration. Those do not become requirements here.
Claude's comment that larger worlds need tiles was technical advice, not an agreed world-size
or streaming contract. Until that scope is selected, pending changes retain the existing 64–8192
single-map limit. No unlimited-world or out-of-core performance guarantee is implied.

## Baseline sequence

| Order | Change | New capability | Prerequisite | PR sections |
| --- | --- | --- | --- | --- |
| Done | terrain-generation | seeded-generation, terrain-heightmap | None | Archived |
| 1 | [water-generation](changes/water-generation/proposal.md) | surface-water | Terrain | Sea/lakes; rivers; CLI/output |
| 2 | [biome-generation](changes/biome-generation/proposal.md) | biome-classification | Water merged | Environmental fields; categories/output |
| 3 | [settlement-generation](changes/settlement-generation/proposal.md) | settlement-placement | Biomes merged | Placement; entity output |
| 4 | [roads-and-bridges](changes/roads-and-bridges/proposal.md) | transport-network | Settlements merged | Graph/bridges; network; output |
| 5 | [border-generation](changes/border-generation/proposal.md) | territory-borders | Transport merged | Partition; boundary output |

Do not start implementation of a downstream change merely because OpenSpec reports its planning
artifacts ready. The prerequisite in its proposal and tasks must be merged first. CLI additions
are cumulative: preserve earlier outputs and tests, and extend the all-file hash comparison.

## Layout extension

[terrain-layouts](changes/terrain-layouts/proposal.md) covers the original local-area/island/world
choice as region, default island and continent-shaped presets. It explicitly modifies the
island/erosion shape promises in terrain-heightmap. It requires water for sea-relative elevations
and is scheduled after the baseline island pipeline; it does not block the next water slice.

Unsigned samples remain heights above the encoded minimum. Water records a sea datum, so
`height / 65535 * height_range_m - sea_level_m` yields signed sea-relative elevation, including
depressions. No signed PNG or change to the current vertical-scale contract is needed.

## Proposed implementation choices

The designs choose concrete defaults so later implementation does not have to invent an API.
These are new planning choices for owner review, not historical agreements:

- Water: boundary-connected ocean, priority-flood lake surfaces, exact catchment accumulation,
  acyclic flat routing and bounded channel symbols.
- Biomes: physical slope, freshwater-distance/noise moisture proxy and six explicit categories.
- Settlements: greedy spaced suitability maxima, kind-specific masks and explicit count shortfalls.
- Transport: A* over dry ground plus bounded cardinal bridges, with a reachable spanning forest.
- Territories: towns as capitals, weighted growth, unclaimed components and exact raster boundaries.
- Layouts: island remains pixel-compatible; region removes forced coast; continent has its own envelope.

Tune documented parameters on reference maps, but do not silently narrow a SHALL requirement to
make implementation fit. In particular, missing routes, cyclic drainage, unsupported sizes or
inadequate hardware performance must not be hidden as successful complete generation.

## Cross-stage output contract

| Stage | Added files |
| --- | --- |
| Current terrain | heightmap.png, heightmap.r16, preview.png, metadata.json |
| Water | water.png |
| Biomes | slope.png, moisture.png, biome.png |
| Settlements | settlements.json |
| Transport | roads.png, roads.json, bridges.json |
| Territories | territories.png, borders.png, borders.json |

All rasters share size, one-metre pixels and top-left x-right/y-down coordinates. Metadata records
every control, version and categorical legend. Entity IDs are stable within identical runs;
references must resolve. Downstream-only parameter changes preserve all upstream data files,
while shared metadata legitimately changes. Every algorithm change bumps both version declarations.

## Later ideas requiring a separate scope decision

- Tile export and genuinely larger-than-8192 worlds: distinguish slicing one existing map from
  generating globally consistent large terrain, drainage and entity networks without holding
  the whole world in memory. Independent per-tile generation is not seamless global hydrology.
- Godot import/rendering or a world-map scene: separate consumer work in retro-game, subject to
  that project's own level-authoring decisions. This repository emits data only.

After the last PR of each change and owner confirmation, synchronize its main specs and archive
it. The release-management implementation is already complete and archived; do not reimplement it.
