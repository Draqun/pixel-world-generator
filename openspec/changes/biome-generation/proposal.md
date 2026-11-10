# Proposal

## Why

The agreed map needs environmental categories, not height alone. Biomes and their slope and
moisture inputs also let settlements and roads avoid unsuitable ground.

## What Changes

- Derive slope in physical units and a deterministic moisture proxy from terrain and water.
- Classify water, grassland, forest, wetland, rock and snow using documented rules.
- Export aligned slope, moisture and biome PNGs with recorded units, thresholds and category IDs.
- Preserve all upstream terrain and water values when biome parameters change.

## Capabilities

### New Capabilities

- `biome-classification`: environmental masks and biome categories derived from terrain and water.

### Modified Capabilities

None. Existing output files remain available.

## Impact

Implementation is blocked until water-generation is merged. Extends the generation pipeline,
Params, metadata, CLI and tests; reuses the grayscale writer. No climate simulation, vegetation
instances, assets or new numerical dependency. See ../../roadmap.md for recovered intent.
