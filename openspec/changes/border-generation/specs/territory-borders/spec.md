# Spec Delta

## Purpose

Partitions generated land into stable territories with settlement capitals and observable borders,
using natural geographic barriers and the completed map's permitted bridge crossings.

## ADDED Requirements

### Requirement: Capitals are existing towns
The requested territory count SHALL be a recorded nonnegative integer. Each placed territory
SHALL have one distinct existing town as its capital and a stable positive ID. Requests exceeding
available towns SHALL use the valid subset and report the shortfall.

#### Scenario: Insufficient towns
- **WHEN** five territories are requested but only two towns exist
- **THEN** at most two territories are created with distinct capital references
- **AND** requested and placed counts are reported

#### Scenario: No capitals requested or available
- **WHEN** the requested count is zero or there are no towns
- **THEN** a valid empty territory list and unclaimed land map are exported

### Requirement: Territory growth respects geography
Territories SHALL grow from capitals with recorded costs that increase for steeper land.
Sea and inland water SHALL remain unclaimed and block growth except at valid exported bridges.
Each assigned land cell SHALL be reachable from its capital in that traversal graph. Land in
components without a capital SHALL remain explicitly unclaimed.

#### Scenario: River barrier
- **WHEN** a river separates a capital from land and no valid bridge joins the banks
- **THEN** territory growth does not cross the river

#### Scenario: Valid bridge
- **WHEN** a generated bridge joins the banks
- **THEN** territory growth can traverse that crossing while water pixels remain unclaimed

#### Scenario: Capital-free island
- **WHEN** an island has no reachable capital
- **THEN** its land remains unclaimed rather than receiving an arbitrary remote territory

### Requirement: Territory and border outputs agree
territories.png SHALL be a 16-bit aligned label layer with 0 for unclaimed/water and positive
territory IDs. borders.png SHALL be an aligned 8-bit mask marking cells adjacent across a
four-neighbour edge to a different positive territory ID. borders.json SHALL record territories,
capital references, requested/placed counts and boundary cell lists grouped by territory pair.

#### Scenario: Two neighbouring territories
- **WHEN** adjacent dry cells have different positive territory labels
- **THEN** their shared boundary appears consistently in the mask and JSON

#### Scenario: Coastline
- **WHEN** a claimed cell borders only water or unclaimed land
- **THEN** that contact is not reported as a border between two territories

### Requirement: Territory generation is deterministic and isolated
Border controls SHALL be validated before output creation. Repeat runs SHALL produce
byte-identical output, including stable label ties and JSON ordering. Changing only border
parameters SHALL preserve every upstream terrain, water, biome, settlement and transport file.

#### Scenario: Territory count change
- **WHEN** only the territory count changes
- **THEN** all upstream file hashes stay identical

#### Scenario: Repeat generation
- **WHEN** identical generation inputs run twice
- **THEN** every output file hash matches

#### Scenario: Invalid territory count
- **WHEN** the count is negative, boolean, fractional or exceeds 65535
- **THEN** generation fails before writing output
