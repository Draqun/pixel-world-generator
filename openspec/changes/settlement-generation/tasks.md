# Tasks

Prerequisite: biome-generation merged. Each numbered section is one PR; open it before the next.
Run make check and add a changelog fragment for each section.

## 1. Suitability and spaced placement

- [ ] 1.1 Add kind-specific land masks, scoring and deterministic greedy spacing using separate streams; verify freshwater preference, fortress elevation preference, dry/in-bounds centres, global spacing, stable ties and source array immutability.
- [ ] 1.2 Add validated counts, spacing and village-radius controls, document proposed defaults and shortfall behaviour, and bump both versions; verify no towns, zero counts, all-water maps, small crowded maps and invalid parameters.

## 2. Entity JSON and pipeline integration

- [ ] 2.1 Export settlements.json with unique kind-prefixed IDs, metre coordinates and requested/placed counts; verify schema, stable order, overlay coordinates and count shortfalls through CLI integration tests.
- [ ] 2.2 Extend all-file determinism/golden tests and document Make examples and an inspected reference placement; verify settlement-only changes preserve all upstream hashes and make check passes.

## Workflow follow-up

- After the final PR and owner visual confirmation, synchronize settlement-placement and archive.
- Roads-and-bridges may begin after this implementation is merged.
