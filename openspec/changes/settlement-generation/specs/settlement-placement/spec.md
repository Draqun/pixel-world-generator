# Spec Delta

## Purpose

Places towns, villages and fortresses using generated geography and exposes stable world-space
entities for later transport, territory generation and external map consumers.

## ADDED Requirements

### Requirement: Settlements occupy suitable land
Settlement centres SHALL lie on dry, in-bounds cells and satisfy recorded kind-specific slope
and biome constraints. Town scoring SHALL favour flat ground with freshwater access; village
scoring SHALL favour habitable land near towns; fortress scoring SHALL favour defensible elevation.

#### Scenario: Unsafe cell
- **WHEN** a candidate lies in water or exceeds its kind's maximum slope
- **THEN** it cannot become a settlement centre regardless of its score

#### Scenario: Geographic preference
- **WHEN** otherwise comparable town candidates differ only in freshwater access
- **THEN** the candidate with better access receives no lower suitability

#### Scenario: Villages without towns
- **WHEN** no town can be placed
- **THEN** villages requiring a town are reported as unplaced
- **AND** independent fortress placement can still proceed

### Requirement: Counts and spacing are explicit
Requested counts and minimum centre-to-centre distances SHALL be recorded and validated.
Placed settlements SHALL satisfy their recorded pairwise spacing. If safe land cannot meet a
request, generation SHALL return the valid subset and report requested and placed counts by kind.

#### Scenario: Crowded small island
- **WHEN** requested settlements exceed available safe, spaced positions
- **THEN** no spacing or land constraint is violated
- **AND** the count shortfall is explicit

#### Scenario: Zero counts
- **WHEN** all requested counts are zero
- **THEN** a valid empty settlement list is exported

### Requirement: Settlement JSON uses stable coordinates and references
settlements.json SHALL contain unique stable IDs, kind, integer x and y coordinates for every
settlement, plus requested/placed counts. Coordinates SHALL use the heightmap's one-metre,
top-left origin. Entity ordering and serialization SHALL be stable across repeat runs.

#### Scenario: Overlay a settlement
- **WHEN** a JSON entity has x=12 and y=34
- **THEN** its centre refers to heightmap row 34, column 12

#### Scenario: Unique IDs
- **WHEN** multiple kinds of settlement are generated
- **THEN** every ID is unique and can be referenced without list-position assumptions

### Requirement: Placement is reproducible and isolated
Placement SHALL use only independent named random streams and recorded parameters. Repeated
runs SHALL produce byte-identical outputs. Changing settlement controls SHALL preserve terrain,
water and biome layers. Invalid counts or spacing SHALL fail before any output is created.

#### Scenario: Placement-only change
- **WHEN** only a town count changes
- **THEN** all upstream layer hashes remain identical

#### Scenario: Repeat generation
- **WHEN** identical generation inputs run twice
- **THEN** every output file hash matches

#### Scenario: Invalid count
- **WHEN** a requested count is negative, fractional or boolean
- **THEN** validation rejects it before writing output
