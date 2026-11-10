# Tasks

Prerequisite: roads-and-bridges merged. Each numbered section is one PR; open it before the next.
Run make check and add a changelog fragment for each section.

## 1. Capitals and geographic partition

- [ ] 1.1 Add stable capital selection and multi-source growth on dry land plus valid bridges; verify capital references, territory connectivity, slope costs, tie ordering, river barriers and capital-free components.
- [ ] 1.2 Add validated count/cost controls, document unclaimed land and count shortfalls in README.md and bump both versions; verify zero towns/count, insufficient capitals, maximum IDs and upstream hash preservation.

## 2. Territory and boundary exports

- [ ] 2.1 Export territories.png, borders.png and borders.json through the writer; verify uint16 labels, stable territory IDs, four-neighbour border detection, no coastline borders, boundary pair ordering and exact JSON/raster correspondence.
- [ ] 2.2 Extend all-output hash/golden tests and document Make examples with an inspected reference partition; verify border-only control changes preserve every upstream file, repeat hashes match and make check passes.

## Workflow follow-up

- After the final PR and owner visual confirmation, synchronize territory-borders and archive.
- The baseline terrain-to-borders island pipeline is then complete; terrain-layouts is an extension.
