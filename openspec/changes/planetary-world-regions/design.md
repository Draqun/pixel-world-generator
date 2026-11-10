# Design

## Context

The current terrain path normalizes a whole `size × size` NumPy array and applies an island mask;
noise depends on array size. Erosion and water hold whole-map arrays, and ocean flood uses image
edges as outlets. Existing `terrain-heightmap` promises an island and full-range normalization.
The former `terrain-layouts` proposal has been absorbed into this change, removing duplicate
ownership of layout and terrain contracts. The owner clarified that island was an example, not
the intended mandatory shape. See proposal.md and the three delta specs for the new contract.

## Goals / Non-Goals

**Goals:** deterministic bounded regional work, physical-size metadata, addressable world
locations, persistent resumable projects, both overview-first and region-first workflows,
meaningful overview-to-detail mapping, and clear fidelity for global water.

**Non-Goals:** a full-resolution global export, real-time game streaming or Godot changes,
exact metre-resolution global water, biomes, settlements, roads or borders in the first terrain
slice. Later layers require separate contracts rather than pretending the current single-image
pipeline already works at planetary scale.

## Decisions

- **Independent axes:** record geometry (`sphere` or `flat`), physical extent and geographic
  intent separately. Flat supports bounded or east-west periodic edges; a sphere is not merely a
  periodic rectangle and has no physical boundary. Region-first generation creates a persistent world definition or uses an existing project;
  its first export bounds are not world boundaries. Unrelated projects remain independent. Island, peninsula, continent and
  local region are meaningful starting presets with recorded extents and documented reference
  fixtures; avoid promising that arbitrary seeds produce a particular coastline without checks.
- **Project lifecycle (implementation choice):** fix geometry, physical world dimensions, origin,
  vertical datum, algorithm versions and geography constraints when creating a project. Users may
  defer all raster generation except the needed region; this does not defer the coordinate frame.
  Later expansion means generating more coverage within this definition, not resizing a sphere or
  stretching a bounded world. Changing those defining choices needs a new project or an explicit
  future migration. Keep an immutable generation definition separate from a canonically ordered
  coverage/artifact index. Resume from persisted data, never process state or a required cache.
  Reject unsupported versions and incompatible overrides before writes. Save artifacts safely,
  publish coverage only for complete exports, and leave previous artifacts intact on failure.
  Region metadata identifies the stable definition, not the changing coverage index; generating
  neighbours must not alter old metadata hashes. Regenerating an overview uses the same field,
  not a new constraint-fitting pass over whichever regions happen to exist.
- **World representation:** persist a versioned manifest with seed, algorithm and step versions,
  geometry, dimensions/radius, projection and units, requested geography, global vertical and
  sea datum, configured overview resolution, sampling rule and stable artifact hashes. The overview
  is optional and can be generated before or after local exports. Its anchor lattice is determined
  by the saved definition even when no overview image exists; adding an overview cannot introduce
  new constraints or change detailed samples. The overview is a
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
  than silently changing those flags. This change owns the former `terrain-layouts` geography
  choices and terrain deltas; do not implement a second standalone preset system first. Island defaults belong only to the legacy
  command. The project workflow requires an explicit recorded geography choice.
  Follow terrain → water → biomes → settlements → roads → borders, one tasks section per PR.

## Section 1 implementation decisions

- `world.json` contains the complete definition and its content-derived SHA-256 identity;
  `coverage.json` separately indexes completed area IDs and relative artifact hashes. Artifact
  metadata will carry area bounds/projections in section 3. The definition's numeric parameter
  pairs are immutable and canonicalized; this slice stores them without inventing terrain rules.
- Coordinate convention version 1 fixes the flat origin at `(0,0)`, x right/y down, and uses
  half-open bounds with only x periodic when requested. Spheres record radius and have no edge.
  The cube-sphere orientation table and x-before-y-before-z seam ownership are in README.md.
- Local spherical conversions use a world-anchored azimuthal equidistant grid. Tangential scale
  error is `(d/R)/sin(d/R) - 1`; reject above 1%. An export must test its farthest corner and
  keep the same anchor for all partitions. No single global square grid is promised.
- Project creation refuses existing directories; load rejects missing fields, unsupported versions,
  identity mismatches and incompatible overrides. Coverage publication verifies artifact hashes,
  refuses removal/replacement of old records, and atomically replaces only its index. Writes
  require one process per project; parallel writers will need locking before they are supported.
- This slice adds a Python foundation API and tests. Make-accessible world/region user commands
  remain section 4. Existing terrain algorithms and output version are unchanged.

## Section 2 sampling contract (defined before implementation)

- Persist `extent` (`world` or `region`) independently of `geography` and physical dimensions.
  It records the starting workflow and never changes terrain samples. Geography uses deterministic
  world-space envelopes for island, peninsula and continent, or unforced terrain for region/world.
  No envelope is fitted to the first requested output. Reference geography uses seed 42, default
  vertical datum and 64 samples across a square bounded flat world; spherical references use the
  same seed and a six-million-metre radius. Guarantees apply to these documented fixtures.
- For flat overviews, the longest image side has `overview_resolution` samples; round the other
  side to the nearest integer, with a minimum of one. Anchor `(column,row)` samples the centre
  `((column+0.5)*width_m/columns, (row+0.5)*height_m/rows)`. The overview covers the whole definition,
  regardless of starting extent. For spheres use `2*resolution` columns and `resolution` rows in
  equirectangular projection; centre samples are longitude `-180+360*(column+0.5)/columns` and
  latitude `90-180*(row+0.5)/rows`. Pixel selections use continuous image-edge coordinates.
- The coarse field is a fixed seeded sum of six sinusoidal waves in normalized flat coordinates
  or unit-sphere Cartesian coordinates, with a separate `world.geography` stream and analytic
  landform envelopes. Integer planar frequencies make the unforced noise periodic in x. Sphere
  envelopes use Cartesian directions/geodesic angles, so no longitude seam becomes a coastline.
  Quantize clipped fractions directly to uint16 in the saved vertical encoding, never normalize
  the overview's minimum and maximum. No erosion or detailed residual is applied in this slice.
- All centre samples are reference anchors, available from the saved definition without an
  overview image. Later regional refinement must preserve their encoded values; it must not
  resample a PNG or independently choose a new coarse field. Five explicit metadata references
  illustrate the lattice; metadata gives formulas for every other sample and marks unresolved
  coastlines/fine detail. This slice does not implement section 3's hierarchical refinement.
- Limit each overview to 1,048,576 samples and process rows in batches of 64. Reject larger
  configured rasters before generation or writes, independent of total physical world area.
  Record metre pixel spans for flat maps; for spheres record angular spans, north-south metre
  scale and east-west scale varying as cosine(latitude), with projection distortion disclosed.
- Export a 16-bit overview and JSON metadata in a new `overview/` directory, then register their
  hashes in coverage. Refuse an existing output rather than overwrite earlier project artifacts.
  World/region CLI integration remains section 4. Schema 2 adds extent; generator 0.5.0 introduces
  the coarse field, retaining standalone terrain/water samples and deliberately updating version
  metadata. Previous foundation manifests require their recorded generator; no implicit migration.

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

Keep legacy files and commands intact. First establish persisted, versioned world projects and
world coordinates; deliver terrain hierarchy and regional exports in independently reviewable PRs,
then integrate navigation and documentation. Bump the generator version for algorithm changes
and update goldens deliberately. Before implementing regional erosion, prove whether the current
catchment-based erosion has bounded dependencies; a local halo is not assumed sufficient for
global accumulation. Specify a compatible world-space method or explicitly reject unsupported
erosion settings rather than claiming seam guarantees without evidence. Roll back the added operations without rewriting existing worlds;
retained manifest versions must fail explicitly when unsupported. Archive only after the final PR
and owner confirmation, per repository workflow.
