# Spec Delta

## Purpose

Make generated world data understandable without repository knowledge by shipping readable
file descriptions, scale explanations and navigation alongside each output.

## ADDED Requirements

### Requirement: Output directories explain their files
Successful standalone-map generation, world-project creation, overview export and region export
SHALL write an English UTF-8 `README.md` in the corresponding output directory. It SHALL identify
the output kind and provide a table of its generated files and their purposes.

#### Scenario: Standalone map
- **WHEN** a standalone map is generated through the CLI or Python writer
- **THEN** its README describes heightmap.png, heightmap.r16, preview.png, water.png and metadata.json
- **AND** distinguishes the 8-bit preview from the authoritative 16-bit height data

#### Scenario: World project and detailed exports
- **WHEN** a project, overview or region is created
- **THEN** its README describes the files belonging to that output kind
- **AND** the project guide explains world.json, coverage.json and the optional overview/ and regions/ directories
- **AND** optional directories are not presented as already generated

### Requirement: Guides explain physical interpretation
Image-output guides SHALL explain dark-to-low and light-to-high grayscale, image dimensions,
coordinate direction, horizontal scale and vertical decoding from saved parameters. Overview
guides SHALL distinguish coarse projection-dependent sampling from one-metre regional pixels.
Guides SHALL state which layers are available or omitted, using the output's recorded contract.

#### Scenario: Coarse world overview
- **WHEN** a world overview is exported
- **THEN** its README explains the saved geometry, projection and physical extent
- **AND** does not describe overview pixels as one metre or sea-datum shading as a river network

#### Scenario: Regional terrain
- **WHEN** a region is exported
- **THEN** its README states its grid location, projection where applicable and one-metre sampling
- **AND** explains shared vertical encoding and points to metadata for projection limits
- **AND** explicitly says that world-linked water and other omitted layers are absent

### Requirement: Reference suites provide an entry point
Each successful regional-reference or overview-reference run SHALL write a README in the suite
directory. It SHALL link the generated project guides and explain fixture names, relevant image
locations and suite-level files. The guide SHALL separate automated assertions from visual
judgment and SHALL NOT present machine-specific timing measurements as deterministic output.

#### Scenario: Regional reference suite
- **WHEN** the six-project regional reference suite finishes
- **THEN** its README explains flat-small, flat-large, sphere-seam and erosion suffixes
- **AND** links each project's README and its overview and regional images using relative paths
- **AND** explains measurements.json and the seam, PNG/R16 and preservation checks

#### Scenario: Overview reference suite
- **WHEN** the overview reference suite finishes
- **THEN** its README explains the eight projects and the row/column layout and shading of reference.png

### Requirement: Documentation preserves export guarantees
README bytes SHALL be deterministic for identical generation inputs regardless of destination,
host, time or export order. Area READMEs SHALL participate in existing artifact hashing and failure
cleanup. Adding guides SHALL preserve existing data bytes, overwrite confirmation and loading of
older projects without READMEs. Existing exports SHALL NOT be retrofitted implicitly.

#### Scenario: Repeat generation
- **WHEN** identical inputs are generated into two fresh destinations
- **THEN** corresponding README file hashes match
- **AND** existing PNG, R16 and metadata bytes remain unchanged by the documentation addition

#### Scenario: Interrupted export
- **WHEN** writing an area README fails
- **THEN** no incomplete area is registered as completed
- **AND** previously published artifacts and coverage remain intact

#### Scenario: Interactive overwrite
- **WHEN** standalone interactive generation targets a directory containing only README.md
- **THEN** replacing that generated file requires the existing overwrite confirmation

#### Scenario: Resume older project
- **WHEN** a valid project without READMEs is reopened and a new region is exported
- **THEN** it remains usable and the new region receives a README
- **AND** previous exports are not modified
