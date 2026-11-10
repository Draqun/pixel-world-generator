# Spec Delta

## Purpose

Classifies generated land using measurable environmental inputs and exports aligned masks that
can be used consistently by settlement placement and transport routing.

## ADDED Requirements

### Requirement: Slope respects the metre scale
Slope SHALL be derived from terrain elevations in metres and one-metre horizontal spacing.
An exported slope.png SHALL encode angles from 0 to 90 degrees into 8-bit values from 0 to 255,
with the conversion recorded in metadata.

#### Scenario: Flat surface
- **WHEN** all terrain heights are equal
- **THEN** slope is zero everywhere, including boundaries

#### Scenario: Known ramp
- **WHEN** a synthetic surface rises one metre per horizontal metre
- **THEN** its interior slope is 45 degrees before image quantization

### Requirement: Moisture is a recorded deterministic proxy
Moisture SHALL combine distance to inland water with an independently seeded moisture field.
It SHALL remain finite in the range zero to one, including maps without freshwater. An aligned
moisture.png SHALL encode that range into 8-bit values with recorded conversion and parameters.

#### Scenario: Freshwater proximity
- **WHEN** two equally elevated flat cells share the same moisture-noise contribution
- **THEN** the cell closer to inland water has moisture no lower than the farther cell

#### Scenario: No inland water
- **WHEN** a map has only sea or no water
- **THEN** moisture stays finite and classification succeeds

### Requirement: Every pixel has one documented biome
An aligned 8-bit biome.png SHALL assign exactly one documented category to every pixel: water,
grassland, forest, wetland, rock or snow. Water SHALL override land categories. Classification
thresholds and precedence SHALL be recorded and testable at their boundaries.

#### Scenario: Water overrides altitude
- **WHEN** a water pixel also satisfies a snow or rock threshold
- **THEN** its biome is water

#### Scenario: Representative land
- **WHEN** synthetic dry cells represent steep ground, high ground, moist low ground and moderate land
- **THEN** the documented rules classify rock, snow, wetland and grassland or forest respectively

### Requirement: Environmental controls preserve upstream outputs
Biome controls SHALL be validated before output creation and recorded in metadata. Repeated runs
SHALL produce byte-identical files. Changing only biome controls SHALL preserve all terrain
and water file bytes and SHALL NOT consume another generation step's random stream.

#### Scenario: Biome threshold change
- **WHEN** only a forest threshold changes
- **THEN** terrain and water hashes remain identical

#### Scenario: Repeat generation
- **WHEN** identical inputs are generated twice
- **THEN** all output file hashes match

#### Scenario: Invalid control
- **WHEN** a threshold is non-finite or outside its documented units and bounds
- **THEN** generation fails before writing output
