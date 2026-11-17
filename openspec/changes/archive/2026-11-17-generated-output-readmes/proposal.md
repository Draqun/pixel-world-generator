# Proposal

## Why

Generated PNG, R16 and JSON files do not explain their purpose or scale. During world-region
review, even locating the overview required knowing the reference project's directory layout.

## What Changes

- Generate an English `README.md` for standalone maps, world projects, overviews and regions.
- Explain each artifact, grayscale heights, physical scale, coordinates, metadata and omitted layers.
- Add an entry-point README to each reference suite, linking its generated projects and explaining
  fixture names, comparison images or measurements and automated checks.
- Keep documentation deterministic and include area READMEs in existing publication/hash handling.
- Preserve existing raster, R16 and metadata bytes; do not retrofit old exports automatically.

## Capabilities

### New Capabilities

- `output-documentation`: Human-readable guides shipped alongside generated data and reference suites.

### Modified Capabilities

None. Existing output format and determinism requirements remain binding; README is additive.

## Impact

The writer, interactive overwrite file list, both reference scripts, output-file assertions and
hash fixtures, repository README, changelog and roadmap are affected. No numerical algorithm,
dependency, CLI option or world schema change is required. Generated English documentation is
part of the output contract; old projects remain readable without it.
