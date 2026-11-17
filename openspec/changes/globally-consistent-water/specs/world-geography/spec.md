# World geography delta

## ADDED Requirements

### Requirement: Overview water is an optional presentation
A hydrology-enabled world SHALL support terrain-only and major-water overview exports using the
same terrain samples, projection, scale and coordinate selection. Major-water presentation SHALL
show qualifying large rivers and lakes plus modelled sea, with recorded physical selection
thresholds and display generalization. Neither variant SHALL require local region exports.

#### Scenario: Compare both world views
- **WHEN** a user exports terrain-only and major-water overviews of the same project
- **THEN** corresponding heightmap samples and coordinate selections agree
- **AND** only the major-water variant includes a water layer and water overlay preview

#### Scenario: Overview is not the complete water inventory
- **WHEN** a small tributary or lake falls below the recorded overview thresholds
- **THEN** its omission is identified as presentation filtering
- **AND** it remains available to detailed regional generation

### Requirement: Overview variants coexist without rewriting coverage
Terrain-only and major-water overview exports SHALL have distinct artifact identities and paths.
Publishing either variant SHALL preserve the other variant, all previously exported regions and
the immutable world definition. Repeating an already published variant SHALL use the existing
no-overwrite behavior. Variant choice SHALL NOT be part of world identity.

#### Scenario: Add major water later
- **WHEN** a terrain-only overview and a detailed region already exist and major water is exported
- **THEN** their original file hashes remain unchanged
- **AND** coverage indexes both overview variants independently in canonical order
