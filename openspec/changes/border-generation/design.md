# Design

## Context

This is the last baseline stage in AGENTS.md. It depends on stable town IDs and the completed
road/bridge crossing contract. No territory or polygon code currently exists.

## Goals / Non-Goals

**Goals:** deterministic capital-rooted territories and boundaries that consumers can overlay.
**Non-Goals:** political history, factions, diplomacy, polygon simplification or border simulation.

## Decisions

- Proposed `borders.py` chooses up to the recorded territory count (default 3, limit 65535)
  distinct towns. Select the first using `step_rng(seed, "borders.capitals")`, then choose
  farthest towns with stable ID ties to avoid clustered capitals. Report fewer towns explicitly.
- Run multi-source Dijkstra over dry land with a cost of step distance times
  `1 + mountain_penalty * slope_degrees / 90` (proposed default penalty 8).
  Inland water and sea block growth; use only bridge entities actually exported in bridges.json,
  with their recorded costs, not all potential crossings considered during road search.
  Bridge water pixels remain label 0; land connectivity is graph connectivity.
- Equal costs prefer the smaller territory ID and then row-major coordinates. Assign labels
  through predecessor propagation so every territory stays connected to its own capital.
  A component with no capital remains 0 instead of receiving a Euclidean nearest owner.
- territories.png uses uint16 IDs, with 0 for unclaimed/water. Derive borders.png from four-way
  contacts between distinct positive labels, marking both banks of such a contact as 255.
  Do not mark coastlines or unclaimed contacts as political boundaries.
- borders.json contains sorted territories (`id`, `capital_settlement_id`), requested/placed
  counts and boundary entries (`territory_ids`, row-major `[x,y]` cells). Use one canonical
  entry per ascending territory-ID pair; no polygon library or ambiguous polygon winding.
- Extend writer, Params, metadata and CLI; bump generator version and test upstream isolation.
  Territory IDs are stable per identical run, not promises of identity across changed parameters.

## Risks / Trade-offs

- [Disconnected islands remain unclaimed] → Intentional contract; add capitals through settlement
  placement settings rather than letting territories jump sea gaps.
- [Large boundary-cell JSON] → The first contract favours exact raster correspondence; measure
  output size, and propose a future versioned geometry change if simplification is required.
- [Sparse capitals produce large territories] → Recorded count and representative previews
  expose this; no hidden faction or population system is introduced.

## Migration Plan

Land capital/partition logic, then output integration in separate PRs after roads-and-bridges.
After owner visual approval, synchronize and archive the final change as the established workflow
requires. Generated files remain the portable artefact, not seed-only game data.
