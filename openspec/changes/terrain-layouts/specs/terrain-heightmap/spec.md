# Spec Delta

## MODIFIED Requirements

### Requirement: Island shape
For island layout, including the default when no layout is selected, the terrain SHALL form an
island: the outer edge SHALL be low ground, and the land SHALL rise towards the interior.
Region and continent layouts SHALL follow their own boundary rules instead.

#### Scenario: Edge is low
- **WHEN** a run using island layout finishes
- **THEN** every pixel on the outer edge of the heightmap is at or below 1 % of the full range

#### Scenario: Interior is higher
- **WHEN** a run using island layout finishes
- **THEN** the mean height of the central quarter of the map is higher than the mean height of the
  outer 10 % band

### Requirement: Hydraulic erosion
The generator SHALL carve the terrain with hydraulic erosion, controlled by an iteration count,
where 0 disables erosion. Erosion SHALL preserve the selected layout's geographic guarantees.

#### Scenario: Erosion disabled
- **WHEN** the user passes `--erosion-iterations 0`
- **THEN** the heightmap is the noise terrain with the selected layout and no erosion applied

#### Scenario: Erosion enabled
- **WHEN** the user passes a positive `--erosion-iterations`
- **THEN** the heightmap differs from the one produced with 0 iterations and still satisfies the
  range and selected layout's shape requirements
