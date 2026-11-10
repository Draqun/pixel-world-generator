# Tasks

Prerequisite: water-generation merged. Each numbered section is one PR; open it before the next.
Run make check and add a changelog fragment for each section.

## 1. Physical slope and moisture fields

- [ ] 1.1 Add pure metre-correct slope and reusable freshwater-distance/moisture calculations with an independent stream; verify flat terrain, 45-degree ramps, edge derivatives, no-freshwater maps, distance monotonicity and repeatability.
- [ ] 1.2 Add finite unit-aware parameter validation, record controls and document the proxy model and encoding in README.md; bump both versions and verify golden changes plus unchanged upstream terrain/water hashes.

## 2. Biomes and exported masks

- [ ] 2.1 Add classification with documented precedence and export slope.png, moisture.png and biome.png through the writer; verify category IDs, threshold equality, water precedence and pixel alignment on synthetic fixtures.
- [ ] 2.2 Integrate CLI/metadata, extend all-output hash/golden tests and document Make examples with a reference preview; verify biome-only changes preserve upstream hashes, repeat runs are byte-identical and make check passes.

## Workflow follow-up

- After the final PR and owner visual confirmation, synchronize biome-classification and archive.
- Settlement-generation may begin after this implementation is merged.
