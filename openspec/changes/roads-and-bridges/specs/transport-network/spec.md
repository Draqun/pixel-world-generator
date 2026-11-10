# Spec Delta

## Purpose

Connects generated settlements through a deterministic geographic transport network and exports
road geometry and bridge references without altering terrain or generating engine-specific scenes.

## ADDED Requirements

### Requirement: Routes respect land traversal constraints
Routes SHALL join settlement centres using connected in-bounds cells and permitted bridge spans.
Land cost SHALL include distance and slope, and SHALL NOT decrease when slope alone increases.
Sea, impassable slopes and unsupported inland-water crossings SHALL be blocked. Diagonal motion
SHALL NOT cut through blocked corners.

#### Scenario: Mountain detour
- **WHEN** an impassable ridge has a passable route around it
- **THEN** a connection uses valid ground rather than crossing the blocked ridge

#### Scenario: Blocked diagonal
- **WHEN** two diagonally adjacent land cells have blocked orthogonal neighbours
- **THEN** they are not connected by a corner-cutting land step

### Requirement: Bridges have valid banks and bounded spans
Each bridge SHALL cross a contiguous river or lake span between dry, traversable banks, within
a recorded maximum length. Bridge geometry SHALL identify its water span and both bank endpoints.
No bridge SHALL cross sea or end inside water. A shared crossing SHALL have one stable entity.

#### Scenario: Short river crossing
- **WHEN** a route crosses a permitted inland-water span with safe banks
- **THEN** the exported route references a bridge matching that span

#### Scenario: Wide lake or sea
- **WHEN** a crossing exceeds the bridge-length limit or touches sea
- **THEN** that crossing is rejected and routing seeks an alternative or reports disconnection

### Requirement: The network reports disconnected components
The network SHALL connect settlements within each component reachable under its traversal rules.
It SHALL report components and unconnected settlement IDs when one global network is impossible.
Zero or one settlement SHALL produce valid empty connection and bridge lists.

#### Scenario: Two islands
- **WHEN** settlements lie on islands separated only by sea
- **THEN** the result reports separate transport components without fabricating a road

#### Scenario: Alternative connection
- **WHEN** a preferred settlement pair has no route but another pair can join their components
- **THEN** the alternative is considered before declaring the components disconnected

### Requirement: Transport outputs agree geometrically
roads.png SHALL be an aligned 8-bit layer with 0 for none, 1 for land road and 2 for bridge.
roads.json SHALL record stable road IDs, endpoint settlement IDs, ordered paths, bridge references
and transport components. bridges.json SHALL record stable bridge IDs and ordered crossing paths.
Every reference SHALL resolve, and raster and JSON geometry SHALL agree.

#### Scenario: Inspect a crossing
- **WHEN** a JSON path traverses a bridge
- **THEN** its referenced bridge exists and its crossing pixels use the bridge raster category

### Requirement: Transport is reproducible without upstream changes
Recorded transport controls SHALL be validated before output creation. Repeated generation SHALL
produce byte-identical outputs. Changing transport controls SHALL preserve terrain, water, biome
and settlement bytes, and routing ties SHALL resolve deterministically.

#### Scenario: Cost-only change
- **WHEN** only a slope-cost control changes
- **THEN** upstream layers and settlements.json remain byte-identical

#### Scenario: Equal-cost routes
- **WHEN** several equally costly routes exist
- **THEN** repeat runs choose the same path and IDs

#### Scenario: Invalid crossing limit
- **WHEN** bridge length is negative, fractional, boolean or non-finite
- **THEN** generation fails before writing output
