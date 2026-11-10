# Tasks

Prerequisite: water-generation merged; schedule after the baseline island pipeline to preserve
its agreed stage order. Each numbered section is one PR; run make check and add a changelog fragment.

## 1. Layout composition and scoped terrain guarantees

- [ ] 1.1 Add island/default, region and continent composition without changing existing island noise/mask draws; verify default/explicit-island pixel equality, unforced region edges and a documented continent land/ocean reference case.
- [ ] 1.2 Scope island/erosion tests to the chosen layout while retaining all existing scenario names, add layout validation and bump both versions; verify full-range PNG/R16 and preview requirements still hold for each mode and update goldens intentionally.

## 2. Full-pipeline layout integration

- [ ] 2.1 Add recorded layout selection to CLI/metadata and document Make examples plus sea-relative depression interpretation; verify invalid modes before output creation, signed sea-relative fixture interpretation and unchanged metre axes/formats.
- [ ] 2.2 Exercise all implemented downstream stages for all layouts and extend byte-identical run tests; verify layer alignment, stage-stream isolation on identical arrays, reference previews and make check.

## Workflow follow-up

- After the final PR and owner visual confirmation, synchronize both terrain specs and archive.
- Large-world export remains a separate scope choice; do not relax single-map bounds here.
