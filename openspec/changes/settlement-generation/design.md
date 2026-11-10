# Design

## Context

Implementation depends on terrain, water and biome stages. Entity generation does not exist yet.
The writer and metadata extensions are planned in water-generation; distance-to-freshwater is
planned in biome-generation. Reuse those after merge rather than implementing parallel helpers.

## Goals / Non-Goals

**Goals:** safe settlement centres and stable entity references for roads and capitals.
**Non-Goals:** interiors, streets, buildings, population, procedural names or lore.

## Decisions

- Proposed `settlements.py` scores arrays and returns plain entity records. CLI/writer own I/O.
  Use separate streams `settlements.towns`, `settlements.villages`, `settlements.fortresses`
  for tie priorities. Stable IDs use a kind prefix and accepted placement order.
- Place towns first, then villages, then fortresses. Greedy score-ranked candidates with a
  spatial occupancy grid provide Poisson-disc-style minimum spacing without a new sampler
  dependency. All ties have deterministic seeded priority then row-major index.
- Candidate masks always exclude water, rock and snow for towns/villages. Default maximum slope
  is 10 degrees for towns, 15 for villages and 25 for fortresses. Fortress candidates must still
  be dry; use elevation and local prominence rather than the flatland score alone.
- Proposed counts are 3 towns, 12 villages and 3 fortresses, default global centre spacing 64 m.
  Town score combines flatness, freshwater proximity and a bonus for river mouths; village score
  combines flatness, habitability and proximity to an existing town within default 512 m.
  Fortress score combines elevation, local prominence and passable surrounding ground.
  Score weights are fixed documented constants for the initial version; do not expose every
  coefficient as a CLI flag. No road-junction bonus: roads do not exist at this pipeline stage.
- JSON shape: `settlements` sorted records with `id`, `kind`, `x`, `y`, plus `counts` mapping each
  kind to requested/placed totals. IDs and positions become input contracts for later changes.
  Counts are upper requests, not a guarantee that invalid sites will be forced into existence.
- Extend Params with counts, spacing and village radius; record thresholds used. Reject invalid
  values before generation. Bump version, test every output hash twice and parameter isolation.

## Risks / Trade-offs

- [Small maps cannot meet default counts/spacing] → Return and expose shortfalls; test 64-pixel
  and all-water fixtures without relaxing suitability. Do not retry indefinitely.
- [Biome borders and numeric scores can tie] → Use stable priorities and fixed candidate order.
- [Greedy sites are not globally optimal] → Deliberate bounded initial algorithm; document
  representative output instead of adding optimization or a city-building simulation.

## Migration Plan

Start only after biome-generation is merged. Implement placement before integration, then add
settlements.json and output contracts in its own PR. Keep all existing raster outputs unchanged.
