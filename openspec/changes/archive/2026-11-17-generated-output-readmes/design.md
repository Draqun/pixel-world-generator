# Design

## Context

See proposal.md for motivation. `writer.py` owns standalone files, project creation and area
publication. Overview files are hash-indexed; regional files are staged before atomic publication.
Project creation removes its files on failure. `interactive.py:OUTPUTS` controls overwrite
confirmation. Both reference scripts create a suite directory containing independent projects.

## Goals / Non-Goals

**Goals:** Extend existing publication paths with small deterministic text renderers and readable
relative navigation. Keep generation steps pure and numerical outputs unchanged.

**Non-Goals:** HTML viewers, new flags, translations, retroactive documentation of old exports,
automatic archival, numerical algorithm changes or a generic documentation framework.

## Decisions

### Render documentation at the output boundary

Use small functions in the writer, taking the same validated parameters/definition/region used
for metadata. Fixed English text plus stable values is sufficient; no template dependency.
Render context-specific guides rather than copying the repository README, which mixes workflows
and cannot describe each export's scale. Keep numerical generation free of documentation I/O.

### Cover each navigation level

Standalone and area guides describe their actual files. A world-project guide explains immutable
definition versus generated coverage and optional directories; it is static after creation, so
later exports do not rewrite old documentation. `coverage.json` remains the live coverage index.
Each reference script writes a suite guide with actual relative project and image paths after
successful generation. It describes measurements without embedding measured times or absolute
output paths. No extra README in the parent OUT directory, which may contain unrelated runs.

### Derive units from each output contract

Describe linear 16-bit height encoding and the relevant datum using existing parameters. Legacy
standalone heights use the local normalized range; world-linked data uses the shared minimum,
range and sea datum. Overview scale follows flat dimensions or spherical projection, not a
universal metres-per-pixel assertion. Mention top-left origin, x right/y down, and regional
projection distortion. Describe water labels only for standalone maps; explicitly list omitted
world-linked layers. Do not add preview images where no preview is currently exported.

### Preserve existing publication semantics

Add README bytes to existing overview/region artifact dictionaries, coverage hashes and cleanup.
Include the project guide in project-creation cleanup. Add README.md to the interactive generated
file list. Keep metadata and area identity unchanged; do not require READMEs when loading older
projects. Existing direct CLI overwrite behavior remains unchanged.

### Additive compatibility

No algorithm or schema version bump is needed: no terrain or metadata contract changes. Update
aggregate golden hashes and exact filename assertions for the additive artifact while checking
old artifact bytes separately. Do not automatically add files to existing completed areas.

## Risks / Trade-offs

- [Misleading scale or grayscale] → Assert guide content against saved metadata for flat and
  spherical overviews and standalone/regional outputs; inspect one complete suite manually.
- [Publication regression] → Exercise README-write failure and verify cleanup/coverage preservation.
- [Documentation drift] → Use the existing validated values and test file tables against output sets.
- [Guide edits invalidate area hashes] → State that area guides are generated indexed artifacts.

## Migration Plan

Ship one slice. New outputs receive guides; old projects continue to load untouched. A rollback
removes README generation while retaining support for coverage entries that already hash README
files. No export deletion or regeneration is required.
