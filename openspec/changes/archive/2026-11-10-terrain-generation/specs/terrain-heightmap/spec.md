# Spec Delta

## Purpose

Defines the terrain heightmap the generator produces: its image format, scale, island shape and
erosion. It is the base layer every later slice (water, biomes, settlements) reads.

## ADDED Requirements

### Requirement: Heightmap image format
The generator SHALL write the heightmap as a single-channel 16-bit grayscale PNG of `size` x `size`
pixels, where one pixel is one metre, with pixel (0, 0) at the top left, x to the right and y down.

#### Scenario: Image header
- **WHEN** a run with `--size 256` finishes
- **THEN** `heightmap.png` is a 256 x 256 PNG with colour type grayscale and bit depth 16

#### Scenario: Default size
- **WHEN** `--size` is not given
- **THEN** the heightmap is 1024 x 1024 pixels

### Requirement: Full height range is used
The heightmap SHALL be normalised so that its lowest pixel is 0 and its highest pixel is 65535.

#### Scenario: Range
- **WHEN** a run finishes
- **THEN** the minimum pixel value is 0 and the maximum is 65535

### Requirement: Island shape
The terrain SHALL form an island: the outer edge of the map SHALL be low ground, and the land
SHALL rise towards the interior.

#### Scenario: Edge is low
- **WHEN** a run finishes
- **THEN** every pixel on the outer edge of the heightmap is at or below 1 % of the full range

#### Scenario: Interior is higher
- **WHEN** a run finishes
- **THEN** the mean height of the central quarter of the map is higher than the mean height of the
  outer 10 % band

### Requirement: Terrain has relief
The terrain SHALL combine large-scale shapes (mountains, basins) with smaller detail, produced by
fractal noise with a configurable number of octaves.

#### Scenario: Octaves recorded
- **WHEN** the user passes `--octaves 4`
- **THEN** the metadata records `octaves` as 4

#### Scenario: Octaves add detail
- **WHEN** the same seed runs with more octaves
- **THEN** the large-scale shape is the same and the heightmap gains finer detail

### Requirement: Hydraulic erosion
The generator SHALL carve the terrain with hydraulic erosion, controlled by an iteration count,
where 0 disables erosion.

#### Scenario: Erosion disabled
- **WHEN** the user passes `--erosion-iterations 0`
- **THEN** the heightmap is the noise terrain with the island shape and no erosion applied

#### Scenario: Erosion enabled
- **WHEN** the user passes a positive `--erosion-iterations`
- **THEN** the heightmap differs from the one produced with 0 iterations and still satisfies the
  range and island-shape requirements

### Requirement: Preview image
The generator SHALL write an 8-bit grayscale PNG preview of the same dimensions, derived from the
heightmap by linear scaling of its 16-bit values.

#### Scenario: Preview matches heightmap
- **WHEN** a run finishes
- **THEN** `preview.png` has the heightmap's width and height, bit depth 8, and each pixel equals
  the heightmap pixel divided by 257, rounded to the nearest integer

### Requirement: Raw 16-bit heightmap
The generator SHALL also write the heightmap as a headerless raw file of `size` x `size`
little-endian unsigned 16-bit values in row-major order, top row first, for engines that import
raw heightmaps.

#### Scenario: Raw matches PNG
- **WHEN** a run finishes
- **THEN** `heightmap.r16` is exactly `size` x `size` x 2 bytes and every value equals the
  corresponding pixel of `heightmap.png`

### Requirement: Vertical scale
The generator SHALL take a height range in metres (`--height-range`, default 400) that states how
many metres the full 16-bit range spans, so a consumer can place 0 at 0 m and 65535 at the range.
The value SHALL be recorded in the metadata and SHALL NOT change any heightmap pixel.

#### Scenario: Recorded in metadata
- **WHEN** the user passes `--height-range 800`
- **THEN** the metadata `params` records `height_range_m` as 800

#### Scenario: Pixels unchanged
- **WHEN** two runs differ only in `--height-range`
- **THEN** their `heightmap.png` and `heightmap.r16` files are byte-identical

#### Scenario: Invalid range
- **WHEN** the user passes a `--height-range` that is zero or negative
- **THEN** it exits with a non-zero status and writes no output files
