# Spec Delta

## Purpose

Defines physically scaled world geography and a manageable overview from which users can choose
locations, while allowing world creation to start at a regional rather than planetary extent.

## ADDED Requirements

### Requirement: World geometry and physical size are explicit
A world definition SHALL record its geometry, physical dimensions in metres and a coordinate
reference. It SHALL support spherical and flat worlds. A flat world SHALL support bounded edges
or east-west wrapping as an explicit choice. A spherical world SHALL have a recorded radius.

#### Scenario: Bounded and wrapping flat worlds
- **WHEN** a flat world is created
- **THEN** its width, height and edge behavior are recorded
- **AND** a bounded world rejects coordinates beyond its edges while a wrapping world maps
  positions one width apart to the same longitude

#### Scenario: Spherical world
- **WHEN** a spherical world is created
- **THEN** its radius and the coordinate convention needed to locate a point are recorded
- **AND** selecting the same physical position across the longitude seam identifies one location

### Requirement: Overview communicates world scale
A world SHALL support an optional manageable overview that identifies the coverage and physical
scale of its pixels. Creating or resuming a project and exporting a region SHALL NOT require
materializing an overview. A user SHALL be able to choose a location or area on it and obtain its world coordinates.
The overview SHALL identify its projection and SHALL NOT claim one overview pixel equals one metre.

#### Scenario: Select a story location
- **WHEN** a user chooses a visible position on the overview
- **THEN** the tool returns its world coordinates and a scale reference for that position
- **AND** the region generated from those coordinates identifies the same location

#### Scenario: Spherical map distortion
- **WHEN** a spherical overview is displayed
- **THEN** its metadata describes its projection and how to interpret distances or distortion

### Requirement: Extent and landform are separate choices
The user SHALL be able to start at world, continent, island, peninsula or local region extent
without first creating a complete world overview. The selected landform SHALL NOT force every
other extent to be an island. Starting from a region SHALL create or use a persistent world project with a recorded identity
and coordinate reference. The initial region bounds SHALL NOT become artificial world boundaries.
A new project SHALL NOT be presented as part of an unrelated pre-existing world.

#### Scenario: Peninsula without an island mask
- **WHEN** peninsula geography is requested for a regional extent
- **THEN** the landform connects to land beyond an edge and has sea along part of its boundary
- **AND** it is not forced to have low ground on every edge

#### Scenario: Island and continent
- **WHEN** an island or continent is explicitly requested
- **THEN** the chosen geography and physical extent are recorded
- **AND** the resulting overview identifies land and surrounding or adjoining sea as appropriate

### Requirement: World and overview are reproducible
The definition SHALL record the seed, generator version, geometry, dimensions and every parameter
needed to recreate its overview and regions. The same definition on the same platform SHALL
produce byte-identical overview artifacts; independent generation steps SHALL use separate streams.

#### Scenario: Repeat a world
- **WHEN** the same definition is generated twice
- **THEN** all overview files and metadata have identical hashes

### Requirement: Project state supports both starting workflows
A project SHALL persist its seed, generator and schema versions, geometry, coordinate convention,
physical dimensions, vertical and sea datum, generation parameters and geographic constraints.
The same project SHALL support overview-first and region-first generation. An island SHALL be
an explicitly selected landform, not a mandatory boundary condition for every project.

#### Scenario: Start with a fragment
- **WHEN** a user creates a project and generates only a selected local area
- **THEN** the project is saved without requiring a world overview
- **AND** its coordinates and generation rules locate future areas in the same world

#### Scenario: Independent projects
- **WHEN** a user creates separate projects for a whole world and for a local area
- **THEN** each project can be saved and resumed independently
- **AND** generating in one project does not mutate the other

#### Scenario: Overview after detail
- **WHEN** a region-first project is reopened and an overview is requested
- **THEN** the overview describes the same world using the already saved generation rules
- **AND** creating it neither changes existing region files nor invents new terrain constraints

### Requirement: Resume preserves the world definition
Reopening a project SHALL restore its generation-defining state without requiring the user to
re-enter settings. Additional coverage SHALL NOT silently change the seed, coordinate origin,
world dimensions, vertical datum, algorithm version or constraints of that project. Unsupported
versions or incompatible settings SHALL fail before overwriting project data. Changing a world's
geometry or dimensions is a separate migration or new project, not ordinary generation of more area.

#### Scenario: Reopen and continue
- **WHEN** a saved project is reopened in a new process on the same supported platform
- **THEN** regenerating an existing area produces byte-identical terrain and region metadata
- **AND** new neighbouring areas use the restored world definition

#### Scenario: Unsupported generator version
- **WHEN** the installed generator cannot reproduce the version recorded by a project
- **THEN** continuation fails with an actionable error before changing saved data
