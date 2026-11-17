# Tasks

Planning only: no implementation is completed. Each numbered section is one PR. For every
section, include its tests and docs, run make check, add a changelog fragment, update both
roadmaps with CLI task counts and remaining slices, open the PR, then stop. Do not begin the next
section before that PR is open. Do not expose incomplete enabled-world generation as supported.

## 1. World hydrology definition and global backbone

- [ ] 1.1 Add the validated immutable hydrology definition/model identity and independent named streams, retaining disabled-world defaults; verify round trips, canonical IDs, invalid finite/unit/threshold/version controls and no-write rejection in focused world/seed tests, and document the pending enabled workflow.
- [ ] 1.2 Implement pure bounded backbone topology, ocean components, seeded priority-flood, terminal basins and physical-area accumulation; verify synthetic inland depressions, no-ocean worlds, true bounded outlets, wrap seams, cube edges/corners/poles, authoritative ocean polygons, coarse coastal islands, area conservation and acyclic routing without touching standalone pixel goldens.
- [ ] 1.3 Add backbone/depth preflight and stable feature/basin IDs, widths and surfaces; verify repeat hashes of serialized pure results, independent stream isolation and allocation bounds, and document the model's ocean convention and estimated drainage units.

## 2. Canonical refinement and shared water geometry

- [ ] 2.1 Add parent-keyed refinement patches, canonical ports and inherited geometry/flux constraints; verify neighbouring patches and cube seams share ports, child routing terminates, local source areas and imported port flux conserve outlet budgets without double counting at a two-parent confluence and parent paths/widths/surfaces do not change when children are queried in opposite orders.
- [ ] 2.2 Add smaller tributaries and parent-owned lake geometry down to the saved minimum scale; verify a confluence, a lake spanning output boundaries, terminal-basin connections and stable feature IDs across cropped, overlapping and whole-area queries, and document excluded subscale features.
- [ ] 2.3 Bound refinement work, geometry complexity and caches without upstream expansion; verify explicit patch/vertex/depth failures and equal-query bounded work on small and planetary worlds, and document resource limits before exposing the solver publicly.

## 3. Water-compatible terrain and versioned enabled worlds

- [ ] 3.1 Add coordinate-defined channel/basin conditioning after existing erosion with bounded influence, common vertical encoding and protected overview anchors; verify an obstructing hill, positive post-quantization sea/river/lake depth, flat lake surfaces, inherited river crossing an anchor, backbone-only anchor ownership, fine tributary detour/exclusion and exclusion of anchors inside new lake polygons and unchanged terrain outside influence.
- [ ] 3.2 Integrate the fully reproducible model into enabled world creation and terrain sampling, bump generator/schema versions and reject incompatible saved projects; verify overview-anchor agreement, partition/overlap/wrap/spherical continuity, reopened/cache-free terrain hashes and identical terrain with water shown or hidden, while preserving disabled/standalone pixel fixtures.
- [ ] 3.3 Expose validated --hydrology selection in world-create and describe model readiness in world-info and generated project guides; verify executable creation examples, disabled defaults, unsupported model/no-write failures and deliberate version-bearing fixture changes, and document that old projects require their recorded generator.

## 4. Optional major-water overview presentation

- [ ] 4.1 Add pure major-feature filtering/generalized water raster and overlay using fixed physical thresholds; verify hidden small features remain in the model, visible subpixel river symbols retain physical-width metadata, sea/lake precedence, matching heightmap bytes and identical coordinate selection in both modes.
- [ ] 4.2 Add keyword-only writer and world-overview --water none|major support with distinct coverage IDs/paths and staged publication; verify both export orders, repeat-variant refusal, JSON/PNG/overlay/guide hashes, failure/cancellation rollback and preserved regional files, and document both existing Make commands and generalized fidelity in output guides.

## 5. Detailed regional water and end-to-end reference evidence

- [ ] 5.1 Add one-metre physical-footprint water.png and stable connected-feature water.json, mode-aware metadata and region-export --water auto|none|detailed; verify category/terrain alignment, dry-region completion, surface/width units, exact/unknown/disabled-mode rejection before generation, and document all files and unresolved scales in regional guides.
- [ ] 5.2 Extend transactional publication, overlap/partition/order/reopen/cache-removal SHA-256 tests to every water artifact and coverage record; verify neighbours preserve existing files, terrain-only/detailed terrain hashes match, spherical cross-projection geometry agrees and interrupted writes preserve prior indexed artifacts.
- [ ] 5.3 Add make water-world-reference with bounded/wrapped/spherical seam/pole examples, both overview modes and detailed major-river/confluence/small-lake crops; verify suite assertions and a navigable README, record peak RSS/work/time separately from deterministic outputs, and deliver images for owner acceptance without starting biomes.

## Workflow follow-up

- After the final slice and owner acceptance, synchronize specs and archive this change in its
  last PR; update both roadmaps together and remove it from their active queues.
- Reconcile biome-generation for the accepted world water contract in a separate request;
  downstream settlement, transport and territory proposals remain blocked until their prerequisites.
