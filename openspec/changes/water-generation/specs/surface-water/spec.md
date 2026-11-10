# Spec Delta

## Purpose

Defines deterministic sea, lake and river geography aligned with the terrain, providing water
constraints for later environmental, settlement and transport generation.

## ADDED Requirements

### Requirement: Sea has a recorded datum and ocean connectivity
Sea SHALL consist of below-sea-level cells connected to the map boundary through below-sea-level
neighbours. The sea datum SHALL be recorded in metres above the encoded height minimum.
Sea-relative elevation SHALL equal encoded elevation in metres minus that datum.

#### Scenario: Enclosed depression below sea level
- **WHEN** low ground lies behind a barrier higher than the sea datum
- **THEN** it is not classified as sea solely because it is below that datum

#### Scenario: Sea-relative depression
- **WHEN** a cell is lower than the recorded sea datum
- **THEN** its interpreted sea-relative elevation is negative without changing its encoded height

#### Scenario: No sea
- **WHEN** no below-sea-level cell touches a boundary
- **THEN** the sea mask is empty and hydrology still terminates

### Requirement: Lakes occupy retained depressions
Depressions with a spill outlet SHALL retain lake water up to that spill level, subject to a
recorded minimum-depth threshold. Sea cells SHALL NOT be reclassified as lakes. Depression
handling SHALL preserve original terrain values.

#### Scenario: Bowl with a spill rim
- **WHEN** a synthetic bowl has a known lowest spill elevation
- **THEN** retained lake cells have positive depth below that surface
- **AND** terrain samples are identical before and after hydrology

#### Scenario: Flat terrain
- **WHEN** a flat map contains no depression below a spill level
- **THEN** no artificial lake or endless drainage loop is introduced

### Requirement: Rivers follow connected drainage
River sources SHALL be selected from accumulated catchment area using a recorded threshold.
Each river centreline SHALL reach sea, a lake, another river or a boundary outlet through adjacent
cells without cycles or increasing routing-surface elevation. Width SHALL grow monotonically
with local accumulation, bounded by a recorded maximum.

#### Scenario: Two tributaries merge
- **WHEN** two catchments drain into one channel
- **THEN** their downstream accumulation includes both contributions
- **AND** the downstream channel is no narrower at equal rendering constraints

#### Scenario: Plateau outlet
- **WHEN** drainage crosses a filled plateau
- **THEN** a deterministic outlet path exists without cycles

#### Scenario: No qualifying catchment
- **WHEN** all catchments fall below the river threshold
- **THEN** an empty river mask is a valid output

### Requirement: Water is an aligned categorical layer
Generation SHALL add water.png as an 8-bit grayscale layer of the heightmap dimensions.
Metadata SHALL define 0 as dry, 1 as sea, 2 as lake and 3 as river. Sea and lake categories SHALL
take precedence where a river joins them. All existing terrain outputs SHALL remain present.

#### Scenario: Layer alignment
- **WHEN** a map of size 128 is generated
- **THEN** water.png is 128 by 128 and shares the heightmap coordinate system
- **AND** each pixel uses a documented category

### Requirement: Water controls are isolated and reproducible
Every water control SHALL be validated before output creation and recorded in metadata.
The same seed, version and parameters SHALL produce byte-identical output files.
Changing only water controls SHALL NOT change heightmap.png, heightmap.r16 or preview.png.

#### Scenario: Water threshold changes
- **WHEN** only the river threshold changes between otherwise identical runs
- **THEN** terrain file hashes remain identical

#### Scenario: Repeat run
- **WHEN** generation is repeated into two directories
- **THEN** every output file has the same SHA-256 in both directories

#### Scenario: Invalid control
- **WHEN** a sea level is non-finite or outside its documented range, or a depth or width is invalid
- **THEN** the CLI fails before creating output files
