# Tasks

Each numbered section is one PR. Open its PR before starting the next section; include the
section's tests, docs, changelog fragment and `make check`. Preserve legacy `generate` behavior
and ship no downstream layer that claims unsupported planet-scale correctness.

## 1. Reconcile scope and establish world coordinates

- [ ] 1.1 Reconcile the overlapping `terrain-layouts` proposal, deltas and task ordering with this
  change before either implementation; validate both changes and show that legacy island defaults
  and the separate new world/region workflows have one unambiguous owner.
- [ ] 1.2 Add a validated versioned world definition and manifest for a sphere and flat bounded or
  east-west wrapping world, including metre dimensions, seeds, parameters, datum and provenance;
  test invalid input before writes and repeat-run byte identity.
- [ ] 1.3 Implement world-coordinate conversions and canonical seam ownership, including sphere
  poles and face boundaries; test round trips, wrapping, distances and documented distortion limits.

## 2. Geographic choices and overview

- [ ] 2.1 Add independent extent and geographic intent selection, including region-first island,
  peninsula, continent and local area; verify deterministic documented reference fixtures and a
  peninsula's land connection without a forced island boundary.
- [ ] 2.2 Generate a bounded-resolution world overview with explicit projection, physical scale,
  reference sample positions and unresolved-detail semantics; test deterministic hashes and
  selection-to-coordinate round trips for both geometries and a 16-million-metre flat world.

## 3. Shared terrain and regional export

- [ ] 3.1 Add coordinate-keyed hierarchical terrain samples and shared vertical encoding,
  preserving overview anchor values; test seed/version isolation, overlap equality and adjacent
  flat-wrap and sphere-face seams without per-region normalization.
- [ ] 3.2 Export selected one-metre regional grids as aligned PNG/R16 and metadata, including a
  world-anchored projection, measured distortion and explicit omitted layers; verify assembled
  tiles against a single area, repeat hashes, invalid-bound failures and unchanged legacy output.
- [ ] 3.3 Implement bounded context for the requested erosion iterations or reject requests that
  exceed the documented resource budget; test seam-free eroded overlap, preflight errors and
  allocation scaling independent of planet dimensions at fixed overview and region sizes.

## 4. Location selection and integration

- [ ] 4.1 Provide Make-accessible world/region commands and an overview-based selection workflow;
  document geometry, scale, output contracts and examples for standalone region and whole world;
  verify the documented workflows and returned coordinates on both geometries.
- [ ] 4.2 Enforce and document water-layer fidelity and availability: no local-edge ocean outlets,
  explicit rejection of unavailable exact global drainage and omitted layers in metadata; test
  failure before output creation and cross-region coarse-water consistency if such data is offered.
- [ ] 4.3 Run end-to-end determinism, reference-sample, seam, physical-scale and resource checks;
  compare two seeds and repeated exports, document measured budgets, update algorithm version and
  deliberate goldens, and run `make check`.

## Workflow follow-up

- Archive only in the last PR after owner confirmation that the world overview and selected regions work.
- Design and implement globally consistent water, then biomes, settlements, roads and borders in
  the project sequence; the terrain milestone does not imply these layers are complete.
