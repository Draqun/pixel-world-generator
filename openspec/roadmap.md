# World generation roadmap and recovered decisions

This is a planning index, not evidence that pending features are implemented. Current main specs
cover seeded terrain, standalone surface water, world geography, regional materialization,
interactive CLI, generated output documentation and release management. Every named pending change has proposal, specs, design
and tasks; implementation requires a separate apply request. Globally consistent water now has
an implementation in progress; the definition, global backbone and canonical refinement are complete; public water export remains unavailable. Each tasks section is one PR.

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

The owner clarified on 2026-11-10 that an island was only an example. The intended product is a
persistent world project: start with a whole-world overview or only a needed region, save it, and
generate further coverage of the same world later without changing existing terrain. Separate
projects are independent. An overview is optional; a first region is not an artificial world edge.

The original discussion did not decide an open-world game, city interiors, factions, names,
weather, ferries, tunnels or engine integration. Those do not become requirements here.
Claude's comment that larger worlds need tiles was technical advice, not an agreed world-size
or streaming contract. The later planetary-world-regions plan now owns bounded-memory overview
and regional export; the existing 64–8192 limit remains a legacy single-map limit, not a world
extent limit. No unlimited-world or real-time streaming guarantee is implied.

## Current status and next sequence

Only unfinished lifecycle work belongs in this table. Archived changes are removed; consult
`changes/archive/` and the changelog for completed work. Status markers follow the
[public roadmap legend](../docs/roadmap.md#status-legend).

| Change | Status | Next action |
| --- | --- | --- |
| [globally-consistent-water](changes/globally-consistent-water/proposal.md) | 🚧 In progress; 6/14 tasks; 3 slices remaining | Backbone and canonical refinement complete; next implement terrain conditioning, then world water exports |
| biome-generation | ⏸️ 0/4 tasks; 2 slices remaining | Await the global water contract; reconcile the single-map proposal before world-linked implementation |
| settlement-generation | ⏸️ 0/4 tasks; 2 slices remaining | Await biomes and a world-linked placement contract |
| roads-and-bridges | ⏸️ 0/6 tasks; 3 slices remaining | Await settlements and a cross-region network contract |
| border-generation | ⏸️ 0/4 tasks; 2 slices remaining | Await transport and a cross-region territory contract |

The unimplemented `terrain-layouts` plan is absorbed into `planetary-world-regions`, not archived
as completed work. Geography selection and terrain contract changes have one owner. Island
remains the legacy command default for compatibility, not the mandatory shape of new projects.

## World project milestone

1. Persist a world definition and reload it: seed, versions, geometry, physical dimensions,
   coordinates, vertical/sea datum, parameters and geography constraints. Separate generation
   rules from generated coverage. Document fixed world dimensions versus deferred materialization.
2. Add geographic choices and optional bounded overview. Its sampling lattice must be defined
   before regional output, even when the overview image is generated later.
3. Generate coordinate-keyed terrain and aligned regional PNG/R16. Verify overlaps, different
   request orders, reopen/resume and later neighbours without changing old file hashes. Prove
   erosion dependencies before promising seamless eroded exports.
4. Integrate both Make-accessible workflows: overview then detail, or region then more coverage
   and optional overview. Record unsupported layers explicitly.

Each numbered tasks section remains one implementation PR. Do not start the next section before
its PR is open. This planning revision does not mark any implementation task complete.

Next review and implement globally-consistent-water in its five PR slices, then reconcile biomes,
settlements, roads/bridges and borders in the binding stage order. Existing downstream plans remain useful for the single-map pipeline; they
are not contracts for cross-region continuity and need reconciliation before world-linked use.
Do not run edge-seeded local water on arbitrary exported regions as if their edges were oceans.

Unsigned samples remain heights above the encoded minimum. With the saved sea datum,
`height / 65535 * height_range_m - sea_level_m` yields signed sea-relative elevation. World-linked
regions share one vertical encoding; only legacy standalone maps normalize over each output.

## Proposed implementation choices

The designs choose concrete defaults so later implementation does not have to invent an API.
These are new planning choices for owner review, not historical agreements:

- Standalone water: boundary-connected ocean, priority-flood lake surfaces, exact raster catchment
  accumulation, acyclic flat routing and bounded channel symbols.
- World-linked water ([proposal](changes/globally-consistent-water/proposal.md)): bounded global
  backbone plus canonical refinement; model-estimated drainage, stable cross-region features,
  optional major-only overview and smaller regional water. New enabled worlds include versioned
  terrain conditioning; water visibility does not change terrain. Exact metre-scale global
  drainage remains unavailable. Technical defaults are proposed choices awaiting review.
- Biomes: physical slope, freshwater-distance/noise moisture proxy and six explicit categories.
- Settlements: greedy spaced suitability maxima, kind-specific masks and explicit count shortfalls.
- Transport: A* over dry ground plus bounded cardinal bridges, with a reachable spanning forest.
- Territories: towns as capitals, weighted growth, unclaimed components and exact raster boundaries.
- World geography: island, peninsula, continent and local area are recorded choices in a persistent
  world project; legacy island remains pixel-compatible. Generation order cannot change terrain.

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

Within each detailed export, rasters share size, one-metre pixels and top-left x-right/y-down
coordinates. World overviews use their separately recorded scale and projection. Metadata records
every control, version and categorical legend. Entity IDs are stable within identical runs;
references must resolve. Downstream-only parameter changes preserve all upstream data files,
while shared metadata legitimately changes. Every algorithm change bumps both version declarations.

## Later ideas requiring a separate scope decision

- Exact global hydrology and cross-region entity networks need separate designs after world terrain.
  Regional terrain and bounded-memory world overview are already in planetary-world-regions scope.
- Resizing a saved finite world or changing its geometry while preserving old areas requires a
  separate migration design; ordinary continuation materializes more of the saved definition.
- Godot import/rendering or a world-map scene: separate consumer work in retro-game, subject to
  that project's own level-authoring decisions. This repository emits data only.

After the last PR of each change and owner confirmation, synchronize its main specs and archive
it. The release-management implementation is already complete and archived; do not reimplement it.
