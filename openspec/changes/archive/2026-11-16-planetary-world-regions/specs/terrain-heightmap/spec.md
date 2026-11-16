# Spec Delta

## MODIFIED Requirements

### Requirement: Full height range is used
A legacy standalone heightmap SHALL be normalised so that its lowest pixel is 0 and its highest
pixel is 65535. World-linked regional tiles SHALL use the common world encoding instead of
normalising each tile independently.

#### Scenario: Range
- **WHEN** a legacy standalone run finishes
- **THEN** the minimum pixel value is 0 and the maximum is 65535

#### Scenario: World-linked tile
- **WHEN** a world-linked tile covers only part of the world's elevation range
- **THEN** it retains the world height datum without stretching the tile to the full range

### Requirement: Island shape
The existing legacy standalone island mode SHALL form an island: the outer edge of the map SHALL
be low ground, and the land SHALL rise towards the interior. Other explicitly selected geographic
extents or landforms SHALL follow their own boundaries and SHALL NOT be forced to be islands.

#### Scenario: Edge is low
- **WHEN** a legacy standalone island run finishes
- **THEN** every pixel on the outer edge of the heightmap is at or below 1 % of the full range

#### Scenario: Interior is higher
- **WHEN** a legacy standalone island run finishes
- **THEN** the mean height of the central quarter of the map is higher than the mean height of the
  outer 10 % band

#### Scenario: Region is not forced into an island
- **WHEN** a peninsula or another non-island region is selected
- **THEN** its outer boundary is not forced low solely because it bounds the output image

### Requirement: Hydraulic erosion
The generator SHALL carve the terrain with hydraulic erosion, controlled by an iteration count,
where 0 disables erosion. Erosion SHALL preserve the selected geography's documented boundary
contract and SHALL NOT introduce seams solely because a world-linked region was partitioned.

#### Scenario: Erosion disabled
- **WHEN** a legacy standalone island run passes `--erosion-iterations 0`
- **THEN** the heightmap is the noise terrain with the island shape and no erosion applied

#### Scenario: Erosion enabled
- **WHEN** a legacy standalone island run passes a positive `--erosion-iterations`
- **THEN** the heightmap differs from the one produced with 0 iterations and still satisfies the
  range and island-shape requirements

#### Scenario: World-linked region is partitioned
- **WHEN** the same eroded world-linked area is generated as one region and as adjacent tiles
- **THEN** corresponding encoded terrain values are identical
