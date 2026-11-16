# Spec Delta

## Purpose

Lets users export detailed terrain for selected places without materializing an entire planetary
raster, while preserving geographic alignment, reproducibility and metre-scale coordinates.

## ADDED Requirements

### Requirement: Generate selected detailed areas
The generator SHALL accept a world definition and a valid selected area and generate only the
requested local area, plus any bounded context needed for continuity. Local output SHALL use
one-metre samples and SHALL record its world identity, geometry, coordinate reference, extent,
resolution, generator version, parameters and shared vertical datum.

#### Scenario: Select a small part of a large world
- **WHEN** a user requests a 1024 by 1024 metre region within a world whose physical extent is
  16,000,000 by 16,000,000 metres
- **THEN** the region is exported without creating a raster at one-metre resolution for the entire world
- **AND** its metadata identifies its location and scale on the overview

#### Scenario: Invalid area
- **WHEN** a request lies outside a bounded flat world's extent or has invalid dimensions
- **THEN** the generator rejects it before creating output files

### Requirement: Detailed output is independent of partition and order
For the same world definition, generation parameters and canonical local grid, matching physical
sample positions SHALL have identical encoded terrain values regardless of region or tile partition,
request order, or whether a neighbouring region was generated first.

#### Scenario: Overlapping requests
- **WHEN** two requests overlap or one area is split into tiles
- **THEN** every common terrain sample has the same uint16 value
- **AND** assembling the tiles yields the same terrain as a single request for the same area

#### Scenario: Wrapped or spherical boundary
- **WHEN** neighbouring locations cross a wrapped edge, a sphere face boundary or a longitude seam
- **THEN** both sides refer to the same continuous world without a discontinuity caused by tile identity

### Requirement: Local height outputs use the world datum
Every detailed tile SHALL use its world's recorded vertical encoding and SHALL NOT independently
stretch its local minimum and maximum. Heightmap PNG and headerless little-endian R16 SHALL
contain matching 16-bit values. All exported raster layers SHALL use the same local grid.

#### Scenario: A tile covers a narrow elevation band
- **WHEN** a tile contains neither the world's minimum nor maximum elevation
- **THEN** its values retain the shared world scale and need not include 0 or 65535

### Requirement: Overview and details describe the same geography
The overview and detailed output SHALL derive from a common world definition and geographic
coordinate mapping. Coarse features and their scale SHALL remain traceable to selected detail;
metadata SHALL state the overview sampling rule and SHALL NOT represent unresolved fine detail
as an exact metre-scale coastline.

#### Scenario: A region is selected from the overview
- **WHEN** the corresponding detailed area is generated
- **THEN** its bounds map back to the selected overview area
- **AND** overview reference samples at the documented sample positions agree with detailed terrain
  after applying the documented quantization rule

### Requirement: Bounded resource use is explicit
The generator SHALL bound memory and storage by the overview, requested region, documented working
context and configured caches, rather than by the total world area at one-metre resolution.
Requests beyond supported per-export limits SHALL fail with an actionable error before writing.

#### Scenario: Large world definition
- **WHEN** the same size region is requested from a small and a much larger world using the same
  overview resolution and settings
- **THEN** no full-resolution world-sized array or output file is allocated for either request

### Requirement: Cross-region water is not misrepresented
World-linked output SHALL identify the coverage, resolution and completeness of every water layer.
It SHALL NOT claim complete global or exact metre-scale drainage from independently processed
regions. If the requested accuracy cannot be produced, the generator SHALL report that limitation
before exporting the layer instead of silently treating region boundaries as ocean outlets.

#### Scenario: River crosses a region boundary
- **WHEN** a water layer is exported for two adjacent regions
- **THEN** any shared coarse network and its precision are consistently identified in metadata
- **AND** the generator does not invent an outlet solely because a river crosses a region edge

#### Scenario: Exact drainage unavailable
- **WHEN** exact world-wide metre-scale catchment data is requested but unavailable
- **THEN** the request fails explicitly without presenting an approximate result as exact

### Requirement: Additional coverage preserves existing regions
Generating additional regions SHALL use the saved project definition and SHALL NOT rewrite
previously generated regions or renormalize their elevations. A project SHALL record generated
coverage and artifact provenance separately from its immutable generation definition; coverage
history SHALL NOT affect terrain samples. Persistent project data SHALL be sufficient to resume
on the same supported platform without relying on transient caches or an earlier process.

#### Scenario: Generate neighbours later
- **WHEN** a user generates region A, closes the tool, reopens the project and generates adjacent region B
- **THEN** every original file for A retains its hash
- **AND** shared sample positions match a fresh combined-area export using the same canonical grid

#### Scenario: Different generation orders
- **WHEN** two copies of the same project generate areas A and B in opposite orders
- **THEN** corresponding regional terrain and metadata files have identical hashes
- **AND** their final coverage records contain the same artifacts in canonical order

#### Scenario: Caches are absent
- **WHEN** only saved project data is retained and disposable caches are removed
- **THEN** the tool can regenerate existing terrain and continue into previously ungenerated coverage
