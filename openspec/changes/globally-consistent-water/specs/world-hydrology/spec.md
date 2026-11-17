# World hydrology

## Purpose

Define persistent water geography that stays continuous across independently generated world
regions and supports coarse presentation without pretending to simulate exact planetary runoff.

## ADDED Requirements

### Requirement: Water geography belongs to the world
A hydrology-enabled world SHALL record its model version, topology, generation scales and all
water and terrain-conditioning parameters in its immutable definition. Water geography SHALL
be independent of requested export bounds, presentation, coverage history and disposable caches.

#### Scenario: Region before overview
- **WHEN** a region is exported before any overview and the project is reopened later
- **THEN** its waterways match an overview-first copy of the same definition
- **AND** creating the overview or neighbours preserves every previous regional artifact hash

### Requirement: Ocean connectivity uses world topology
Sea SHALL follow globally identified below-datum ocean components, respecting bounded flat,
wrapped flat and spherical topology. Enclosed below-datum basins SHALL NOT become sea solely
because of their elevation. Export edges SHALL NOT be treated as ocean seeds or new outlets.

#### Scenario: Inland region boundary
- **WHEN** a river or an enclosed below-datum basin crosses an inland export boundary
- **THEN** the boundary does not reclassify that water as sea or terminate its world feature

#### Scenario: Closed world without ocean
- **WHEN** a spherical world has no below-datum ocean component
- **THEN** the ocean mask is empty and drainage terminates in identified inland terminal basins

### Requirement: Coarse and fine water share feature identity
Detailed water SHALL retain inherited major river paths, connections, lake surfaces and stable
feature identities. Refinement SHALL add smaller tributaries and water bodies without moving
inherited geometry. Features below the recorded minimum generation scale SHALL remain unresolved;
absence from an overview SHALL NOT imply absence from the world.

#### Scenario: Zoom to a major river
- **WHEN** a detailed region covers part of a major river visible on the overview
- **THEN** the river has the same world identity and course, subject only to recorded rasterization
- **AND** smaller tributaries can appear without changing that river's course

#### Scenario: Small lake hidden at world scale
- **WHEN** a qualifying small lake is omitted from the major-water overview
- **THEN** exporting its region reveals that same persistent lake regardless of export size or order

### Requirement: Regional water is partition independent
For the same world definition and canonical grid, matching physical samples SHALL have identical
water categories and conditioned terrain regardless of export partition, request order or caches.
Cross-boundary water features SHALL share identity, width and surface elevation. Different
spherical projections SHALL reference the same world geometry without promising identical pixels.

#### Scenario: Split and overlapping exports
- **WHEN** one area is exported whole, as adjacent tiles and as overlapping requests
- **THEN** matching sample values agree for both water and terrain
- **AND** assembling the adjacent tiles reproduces the whole-area rasters

#### Scenario: Geographic seams
- **WHEN** a feature crosses wrapped longitude, a cube-face boundary or a pole
- **THEN** canonical feature ownership preserves its course and connections
- **AND** same-grid seam checks and world-space comparisons across projections both pass

### Requirement: Water follows a terminating network
Every river SHALL connect to sea, a lake, another river, an explicit terminal basin or an actual
bounded-world outlet. Routing SHALL be acyclic and its water surface non-increasing downstream.
Rivers SHALL have recorded physical widths and drainage-size estimates that do not decrease at
confluences. Detail SHALL NOT retroactively change inherited widths or drainage estimates.

#### Scenario: Tributaries merge
- **WHEN** two smaller channels join an inherited river
- **THEN** the connection is continuous and downstream water is no narrower
- **AND** its inherited drainage budget remains unchanged by which tributaries were materialized

#### Scenario: Landlocked plateau
- **WHEN** routing has no ocean outlet
- **THEN** it terminates at an explicitly identified basin or true world boundary without cycles

### Requirement: Terrain accommodates prescribed water
In hydrology-enabled worlds, channel and basin conditioning SHALL be part of versioned terrain
generation, independent of water visibility. Wet channel beds and lake beds SHALL lie below their
recorded surfaces after height quantization. Terrain and water SHALL share the world datum and
preserve overview reference-sample agreement. Existing exports SHALL NOT be modified to add water.

#### Scenario: River crosses fine relief
- **WHEN** raw regional relief would obstruct an inherited river
- **THEN** deterministic conditioning accommodates the channel within its documented corridor
- **AND** the exported bed is below the non-increasing water surface

#### Scenario: Hide water
- **WHEN** the same hydrology-enabled area is exported with water included and omitted
- **THEN** its heightmap PNG, R16 and terrain-derived preview have identical hashes

### Requirement: Water outputs distinguish geometry from depiction
Detailed exports SHALL provide aligned categorical water.png with 0 dry, 1 sea, 2 lake and 3 river,
with sea then lake precedence over river, and water.json identifying intersecting features,
connections, physical widths and surface elevations. Overview water SHALL be labelled generalized;
minimum display widths SHALL NOT be represented as physical channel widths.

#### Scenario: Narrow river on a world image
- **WHEN** a qualifying major river is narrower than one overview pixel
- **THEN** a visible symbol can represent it and metadata states its generalized footprint
- **AND** regional water.png uses the physical footprint sampled on its one-metre grid

### Requirement: Fidelity and limits are explicit
Water metadata SHALL record model identity, generation scales, resolved coverage, physical units,
conditioning parameters and unresolved detail. Drainage area SHALL be labelled model-estimated,
not exact metre-scale catchment area. Requests for exact planetary metre-scale drainage SHALL
fail before writes. A dry or below-resolution result SHALL NOT be reported as missing processing.

#### Scenario: Unsupported accuracy
- **WHEN** exact global metre-scale drainage is requested
- **THEN** the tool rejects it with an actionable explanation and preserves project files

#### Scenario: Fully processed dry region
- **WHEN** a supported region contains no modelled water
- **THEN** it exports an all-dry layer and an empty feature list with complete model-coverage metadata

### Requirement: Resource use is bounded by canonical working context
Generation SHALL use a bounded global backbone plus only the canonical refinement cells and
feature context needed by the request. It SHALL NOT materialize a metre-resolution world raster
or recursively expand through every upstream region. Documented work, memory and hierarchy limits
SHALL be checked before publishing any artifacts or coverage.

#### Scenario: Remote catchment
- **WHEN** a region contains the downstream end of a long river
- **THEN** its drainage budget comes from the saved model rather than generating upstream metre tiles

#### Scenario: Unsupported resource demand
- **WHEN** backbone, refinement or geometry complexity exceeds a supported budget
- **THEN** the request fails without incomplete exports or changes to existing coverage

### Requirement: Reproducibility includes all water artifacts
Identical seed, version and parameters on the same platform SHALL produce byte-identical water
and terrain artifacts, JSON, metadata and guides. Hydrology steps SHALL use independent named
random streams and stable feature ordering. Water-enabled world creation SHALL validate the model
before writes; incompatible projects SHALL fail without implicit migration.

#### Scenario: Regenerate after cache removal
- **WHEN** the same exports are generated in two fresh destinations with opposite request order,
  process restarts and all disposable caches removed
- **THEN** corresponding artifact SHA-256 hashes match
- **AND** canonical coverage records identify the same completed exports

#### Scenario: Recorded model is unsupported
- **WHEN** an older or unknown generator or hydrology model cannot be reproduced
- **THEN** continuation fails before writing and explains how to use the compatible generator
