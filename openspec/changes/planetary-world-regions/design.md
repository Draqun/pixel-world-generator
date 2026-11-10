# Design

## Context

The current terrain path normalizes a whole `size × size` NumPy array and applies an island mask;
noise depends on array size. Erosion and water hold whole-map arrays, and ocean flood uses image
edges as outlets. Existing `terrain-heightmap` promises an island and full-range normalization.
The pending `terrain-layouts` change modifies those same promises and excludes tiles. See
proposal.md and the three delta specs for the new product contract.

## Goals / Non-Goals

**Goals:** deterministic bounded regional work, physical-size metadata, addressable world
locations, meaningful overview-to-detail mapping, and clear fidelity for global water.

**Non-Goals:** a full-resolution global export, real-time game streaming or Godot changes,
exact metre-resolution global water, biomes, settlements, roads or borders in the first terrain
slice. Later layers require separate contracts rather than pretending the current single-image
pipeline already works at planetary scale.

## Decisions

- **Independent axes:** record geometry (`sphere` or `flat`), physical extent and geographic
  intent separately. Flat supports bounded or east-west periodic edges; a sphere is not merely a
  periodic rectangle and has no physical boundary. Regional-first generation creates a standalone
  definition, not a fictitious subset of another world's seed. Island, peninsula, continent and
  local region are meaningful starting presets with recorded extents and documented reference
  fixtures; avoid promising that arbitrary seeds produce a particular coastline without checks.
- **World representation:** persist a versioned manifest with seed, algorithm and step versions,
  geometry, dimensions/radius, projection and units, requested geography, global vertical and
  sea datum, overview resolution, sampling rule and stable artifact hashes. The overview is a
  finite, explicitly scaled product, not a resampled 16-million-square allocation. An overview
  pixel is a sample, not a promise that its entire footprint is uniformly land or sea. Maintain
  exact overview anchor samples at defined world locations and refine between anchors; classify
  coastlines between anchors as unresolved rather than claiming exact outlines.
- **Coordinates and spherical metric:** flat coordinates are metres on a planar grid. For a
  sphere, use a documented canonical cube-sphere atlas with stable face orientation, seam
  ownership, conversion to longitude/latitude and radius-based surface distances. Overview may
  use a longitude/latitude display projection with explicitly documented distortion. Export a
  local metre grid using a world-anchored local projection with its origin and orientation in
  metadata. A curved surface cannot be mapped to one globally undistorted square grid: record
  measured maximum scale error for each export, validate a documented tolerance and reject
  extents that exceed it rather than labeling distorted global pixels as exactly one metre.
  Partition-independent comparisons apply to matching world sample positions on the same canonical
  local grid; crossing chart edges uses the recorded face mapping. Test poles, seams, and the
  distance tolerance, including multiple adjacent tiles. A single global equirectangular raster
  with fixed metres per pixel is rejected because it distorts distances with latitude.
- **Hierarchical field and seams:** base all generated values on global positions, master seed,
  step name and stable spatial keys, not chunk order or per-request RNG history. Choose an
  anchored hierarchical field with deterministic interpolation and zero residual at overview
  anchors so overview and detail share reference samples. Use fixed global elevation encoding;
  quantize once with that scale, never per tile. Pure operations take coordinates and explicit
  random streams; I/O remains in the writer/CLI. Generate bounded halos sufficient for every
  finite-support operation, crop after processing and verify overlap hashes. Erosion must have
  a proven finite dependency radius for the configured iterations; if resource limits cannot
  support the required halo, reject before output, do not silently truncate. Alternatives of
  independent tile noise, per-tile normalization or fixed local boundaries create visible seams.
- **Water and future features:** do not run the current boundary-seeded priority flood on each
  tile and call it global water. A separately versioned overview-scale hydrology product may
  provide a coarse drainage backbone; record scale, provenance and accuracy. Region edges are not
  ocean outlets. Exact global metre-scale drainage is unavailable unless a later design provides
  it; reject requests for that guarantee. Provide terrain-only regional exports initially, with
  explicit metadata for omitted layers, rather than writing incorrect `water.png`. Biome,
  settlement, road and border placement require later cross-region ownership and consistency
  designs in the established project sequence.
- **Bounded use:** overview resolution and maximum local output/halo have explicit validation and
  measured resource budgets. Planetary physical dimensions must not allocate a proportional
  full-resolution grid. Keep paths and identifiers stable, avoid timestamps, validate before
  creating files and write only requested areas. Tests compare files and global sample values,
  include a 16-million-metre reference extent, and instrument allocation behavior without
  attempting the impossible full-resolution output.
- **Compatibility and overlapping plan:** preserve the legacy `generate` path, default island,
  heightmap/preview bytes and existing size bounds. Provide new world/region operations rather
  than silently changing those flags. The pending `terrain-layouts` delta and its tasks overlap
  island/default/boundary requirements; reconcile them with this change in the first PR before
  applying either overlapping contract. Its standalone presets are not proof of world continuity.
  Follow terrain → water → biomes → settlements → roads → borders, one tasks section per PR.

## Risks / Trade-offs

- [Spherical grids cannot preserve all metre distances globally] → record projection and measured
  distortion; enforce a defined tolerance on local exports and test seams and poles.
- [Global water needs more than local halos] → label coarse products and reject unavailable exact
  drainage; design a separate world-scale hydrology stage before promising it.
- [Large iteration halos or dense regional requests can exceed RAM] → preflight size and budget;
  document limits and test failure before output creation.
- [Overview may hide a coastline or feature below its sampling resolution] → expose its resolution
  and sample semantics; do not promise terrain is uniform within an overview pixel.
- [Spatial keys or version changes alter reproducibility] → persist versions and parameters,
  use stable hashing and verify repeated and differently partitioned runs on the same platform.

## Migration Plan

Keep legacy files and commands intact. First reconcile pending spec deltas and establish versioned
world definitions; deliver terrain hierarchy and regional exports in independently reviewable PRs,
then integrate navigation and documentation. Bump the generator version for algorithm changes
and update goldens deliberately. Roll back the added operations without rewriting existing worlds;
retained manifest versions must fail explicitly when unsupported. Archive only after the final PR
and owner confirmation, per repository workflow.
