# Proposal

## Why

The owner asked for towns, villages and fortresses placed using the generated geography.
This stage turns environmental layers into reusable world entities without building city interiors.

## What Changes

- Score dry candidate locations by terrain, freshwater access and biome suitability.
- Place spaced towns, villages around towns, and fortresses on defensible high ground.
- Export stable entity IDs, kinds and metre coordinates in JSON, with requested/placed counts.
- Report insufficient suitable land rather than placing entities in water or violating spacing.

## Capabilities

### New Capabilities

- `settlement-placement`: deterministic, geography-aware settlement entities and spacing.

### Modified Capabilities

None.

## Impact

Implementation is blocked until biome-generation is merged. Adds placement functions and JSON
serialization alongside the existing CLI writer; extends Params, metadata and determinism tests.
No buildings, population simulation, lore, game scenes or naming system. Candidate scoring details
are proposed implementation choices, not recovered owner decisions; see ../../roadmap.md.
