# Spec Delta

## Purpose

Supports the original choice between a local land area, island and continent-shaped map without
changing the pixel scale, existing height formats or downstream layer coordinate system.

## ADDED Requirements

### Requirement: Layout selection is explicit
Generation SHALL accept island, region and continent layouts and SHALL record the selected layout
in metadata. Island SHALL remain the default. An unsupported layout SHALL be rejected before
output creation. Single-map size limits SHALL remain 64 through 8192 pixels.

#### Scenario: Omitted layout
- **WHEN** a run omits layout selection
- **THEN** it uses island layout

#### Scenario: Explicit island
- **WHEN** the same inputs explicitly select island
- **THEN** terrain samples match a run using the default layout

#### Scenario: Unsupported layout
- **WHEN** an unknown layout is selected
- **THEN** generation fails before writing output

### Requirement: Layouts have distinct geographic boundaries
Region layout SHALL use terrain without a forced island falloff, allowing raised land at map
boundaries. Continent layout SHALL shape a coherent landmass with at least one land boundary
and one ocean boundary under its documented reference parameters. Neither layout SHALL promise
the all-low edge ring required for islands.

#### Scenario: Region boundary
- **WHEN** a synthetic nonzero terrain field is composed as a region
- **THEN** its boundary is not zeroed by an island mask

#### Scenario: Reference continent
- **WHEN** the documented reference seed and continent parameters are generated
- **THEN** dry land reaches at least one boundary and sea reaches another

### Requirement: Layout changes preserve data contracts
Every layout SHALL preserve 16-bit PNG and matching little-endian R16, full-range encoding,
one-metre pixels and aligned downstream layers. Sea-relative depressions SHALL use the recorded
sea datum without signed-height encoding. A layout SHALL NOT change another stage's random stream.

#### Scenario: Depression in a region
- **WHEN** region terrain contains ground below the sea datum
- **THEN** consumers recover a negative sea-relative elevation from metadata and unsigned samples

#### Scenario: Repeat a layout
- **WHEN** identical inputs for one layout are generated twice
- **THEN** every output file hash matches
