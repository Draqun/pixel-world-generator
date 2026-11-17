# Roadmap

Only unfinished work is listed below. Remove archived changes from the queue; their history
remains in `openspec/changes/archive/` and the changelog.

| Order | Change | Scope | Status / next step |
| --- | --- | --- | --- |
| 1 | [globally-consistent-water](../openspec/changes/globally-consistent-water/tasks.md) | Shared hierarchical water, optional major-water overview and smaller regional waterways | 🚧 In progress; 6/14 tasks; 3 slices remaining; backbone and canonical refinement complete, terrain conditioning and public water export pending |
| 2 | [biome-generation](../openspec/changes/biome-generation/tasks.md) | Physical slope, moisture and biome layers | ⏸️ 0/4 tasks; 2 slices; world-linked implementation awaits the global water contract and reconciliation of the single-map proposal |
| 3 | [settlement-generation](../openspec/changes/settlement-generation/tasks.md) | Towns, villages and fortresses | ⏸️ 0/4 tasks; 2 slices; awaits biomes and a world-linked placement contract |
| 4 | [roads-and-bridges](../openspec/changes/roads-and-bridges/tasks.md) | Terrain-aware roads and river crossings | ⏸️ 0/6 tasks; 3 slices; awaits settlements and a cross-region network contract |
| 5 | [border-generation](../openspec/changes/border-generation/tasks.md) | Territories and border layers | ⏸️ 0/4 tasks; 2 slices; awaits transport and a cross-region territory contract |

## Status legend

- 📝 Proposed: artifacts exist but implementation has not started; an unlinked entry still needs a proposal.
- 🚧 In progress: proposal or implementation work is underway, including an open PR.
- ✅ Complete: all tasks are checked; owner acceptance, spec synchronization or archive remains.
- ⏸️ Blocked: the row names the dependency or decision needed to continue.
- 📦 Archived: complete and archived; remove the row from this queue.

Task counts come from `openspec list --json`. Keep them and slice counts current as work lands.
