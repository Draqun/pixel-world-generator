# Design

## Context

See proposal.md for motivation. `WorldDefinition` currently has schema 2 and includes the
installed generator version in its content identity. `overview_resolution` defines a saved
sampling lattice, not just a freely changeable image size. `generate_overview` samples the coarse
geography field; `generate_region` adds coordinate-keyed detail and bounded erosion while
restoring those reference samples. Keep that agreement.

`water.drainage` seeds every image boundary, and `accumulation` counts standalone raster cells.
Neither constitutes global world hydrology. `region_metadata` and `write_region` currently reject
all water except `none`. `write_overview` publishes a single `overview` coverage record;
`write_region` already stages files and preserves indexed output on interruption. The standalone
Textual interface is not a saved-world browser; extending it is outside this change.

The owner's requested behavior is two world views (without water or with the largest waterways),
with smaller rivers and water bodies revealed by regional generation. Technical choices below
are this proposal's recommendations, not claims of prior owner approval or proven performance.

## Goals / Non-Goals

**Goals:** One immutable procedural water geography; world-space continuity and deterministic
materialization; explicit coarse/fine fidelity; bounded work; channels consistent with terrain.
Support bounded flat worlds, wrap-x worlds and spheres, including seams and poles.

**Non-Goals:** Exact planetary metre-scale runoff, rainfall/discharge simulation, seasonal water,
deltas or braided channels, underground flow, water animation, game integration, arbitrary zoom
UI, retrofitting old exports or implementing downstream biome/settlement/transport proposals.
Small water means features above a finite recorded generation scale, not every possible puddle.

## Decisions

### 1. Use a hierarchical procedural model

Alternatives considered:

- Run the existing solver per requested region: cheap, but changes outlets with export bounds.
  Even a fixed halo cannot resolve arbitrarily distant drainage dependencies. Rejected.
- Solve the complete world at one metre, possibly out of core: closer to exact drainage but work
  and storage scale with world area and defeat deferred planetary materialization. Rejected.
- Solve a bounded global backbone and deterministically refine canonical cells on demand:
  selected. Preserves geography while explicitly approximating catchments and fine terrain.

This adapts the general idea of hydrology-driven procedural terrain, rather than claiming to
implement a published algorithm verbatim. Background: [Genevaux et al., 2013](https://www.cs.purdue.edu/cgvlab/www/publications/Genevaux13ToG/).
Use priority-flood for bounded routing problems, with explicit seeds and stable tie-breaking;
see [Barnes et al., 2014](https://arxiv.org/abs/1511.04463). Neither source proves this proposed
hierarchy's continuity; synthetic invariants and reference fixtures are required evidence.

Add a pure `world_water.py` module, keeping I/O in `writer.py` and CLI orchestration in
`world_cli.py`. Reuse `step_rng` with separate `world.water.backbone`, `world.water.refinement`
and `world.water.basins` names, then stable keys from canonical cell/feature identifiers.
Never advance a shared RNG according to query traversal order. Keep legacy `water.py` unchanged
unless extracting a genuinely reusable primitive preserves its standalone regression fixtures.

### 2. Persist the model separately from presentation

Add a validated hydrology definition in schema 3: `model` is `none` or `hierarchical-v1`, with
all versioned generation constants expanded in saved JSON. New project creation retains `none`
as the compatibility default; `--hydrology hierarchical` explicitly enables the new model.
Algorithm changes bump the generator version. Model identity hashes the immutable generation
definition and water parameters; paths, coverage, caches and display mode are excluded.

Proposed v1 constants/defaults (implementation decisions, adjustable during review):

| Setting | Default / limit | Role |
| --- | --- | --- |
| Backbone resolution | 64 cells per long flat axis / per cube-face axis | Global topology, independent of overview image |
| Refinement factor | 4 per axis | Canonical child cells, at most 16 per parent |
| Target finest cell span | 64 m | Routing detail, not output pixel size |
| Maximum refinement depth | 16 | Reject worlds that cannot reach the target within this depth |
| Minimum river drainage estimate | 1,000,000 m² | Physical feature selection |
| Minimum lake area / retained depth | 4,096 m² / 0.5 m | Physical feature selection |
| Major river / lake display thresholds | 1,000,000,000 m² / 1,000,000 m² | Overview presentation defaults |
| Physical channel width cap | 64 m | Bounded feature/context footprint |

Sub-64 m routing is unresolved, although continuous geometry is sampled into one-metre exports.
Do not call a one-metre raster a one-metre catchment solution. Very small worlds can have no
qualifying rivers or lakes; this is a valid processed result. Validate positive finite sizes,
consistent thresholds, depth and width limits and vertical encoding before project creation.
Presentation thresholds only filter existing physical features and cannot create new water.

### 3. Backbone topology and oceans

For flat worlds use a rectangular cell graph with physical aspect ratio (at least one cell on
each axis); wrap x only when recorded. For spheres use six canonical cube-face grids and shared
edge ownership via `coordinates.py`; compute cell areas and distances on the sphere, not as
latitude-independent image pixels. IDs are topology + face + level + integer cell coordinates;
fixed face ordering and smallest canonical ID break edge/corner ties.

Sample coarse geography, build below-sea connected components and record ocean roots. On bounded
flat worlds, only components connected to actual below-datum world boundaries seed sea. On
closed/wrapped topologies without such a root, select the largest below-datum component as the
model ocean, ties by smallest cell ID; other enclosed components remain basins. A wrapped world's
real north/south boundaries are considered first. If none is below datum, there is no ocean.
This is a recorded coarse ocean convention, not a proof of exact fine-resolution connectivity.

Priority-flood from ocean roots and real bounded-world outlets establishes an acyclic drainage
forest, filled levels, depression groups and topological ranks. A fully closed ocean-free graph
uses its lowest cell (ID tie-break) as an explicit terminal basin root. Lakes have stable basin
IDs, spill surfaces and outlet connections; terminal lakes are explicitly marked without an
invented sea or region-edge outlet. Assign physical cell-area budgets and accumulate in stable
topological order. Counts are exact on this chosen graph; their interpretation as real terrain
catchment area is approximate. Major features are selected from this complete backbone.

Implementation detail for slice 1: each quadrilateral parent owns one centre routing site,
its physical cell area and one prescribed downstream edge port or true world outlet. Incoming
flux and the cell's own source area remain distinct. Spherical areas sum the two physical
triangles of each quad. Integer cube keys make shared edge/corner ownership exact. Retained lake
cells route to one deterministic spill before recomputing ranks and accumulation.

Shoreline geometry uses a separate fixed eight-triangle fan per cell: centre, shared edge
midpoints and corners. Edge heights average the adjacent centre samples; corner heights take
the maximum incident sample, preventing diagonal low cells from connecting across a dry cell.
This supplies a continuous piecewise-linear coarse shoreline while the parent routing domains
remain quadrilateral. Future refinements consume the prescribed shared ports and frozen geometry.
The internal definition round-trips independently; saved schema 3 and enabled-world persistence
remain in slice 3, so earlier slices cannot publish incompatible unconditioned worlds.

### 4. Refine canonical cells, never output rectangles

A refinement patch is one whole parent cell and its 4 by 4 child graph. Its inputs are the parent
routing rank, inherited channel/basin geometry, outlet ports, surfaces and drainage budget.
Construct shared ports once using the canonical owner of each parent edge; transport coordinates
across face seams through the canonical cube mapping. Opposite sides consume the same port data.

Each patch samples the existing coordinate-keyed terrain as a suitability field. Route child
tributaries with an explicitly seeded priority-flood toward inherited channels, inherited lakes,
or the parent's prescribed outlet. No child chooses an arbitrary patch edge as an outlet.
All internal paths decrease a stable routing rank; all external transitions inherit the parent
DAG. Parent river geometry and parent lake footprints/surfaces are immutable obstacles/targets:
refinement adds features but cannot meander an already published parent river or resize its lake.
Geometry may be subdivided without changing its world-space locus.

Keep two quantities separate: the parent's local source area and imported upstream flux.
Subdivide only local source area among children by physical area in fixed order, with a residual
correction so the sum equals the parent local area. Inject each imported port flux exactly once
at its owning child. Accumulate through the child DAG, requiring parent outlet flux to equal
parent local area plus all imported flux (or record that budget at a terminal basin). A parent
cell has one prescribed downstream outlet; children cannot repartition its flux to a different
neighbour. Refined contributions replace coarse allocation, never supplement it. These are
procedural drainage budgets, not recomputed fine-terrain catchments. Width is a bounded monotone
function of that model budget,
`min(64, max(1, sqrt(area_m2 / 1_000_000)))` metres. No later query changes a parent width.

The internal implementation uses rectilinear carrier paths with exact rational/cube-vector port
identities. Constraints stop at the prescribed outgoing interface; boundary-only curves carry
transport only when an imported port matches their profile. Sea/lake polygons take surface
precedence over covered curve segments. Ordinary child interfaces crossing an active inherited
carrier use that curve's surface; upstream potentials accommodate the shared datum without
changing the carrier's exact locked ports. Low prescribed inlets use constrained least-excavation
routes around higher immutable carriers. New geometry is excluded if its first physical
contact lies below the containing child's prescribed outlet, preventing a new incidental sink.
New curves explicitly preserve all crossed transport-point datums. Low inlet paths may use
an exact shared outlet corner instead of a higher edge midpoint. Candidate carriers undergo a
bounded, terrain-free feasibility check of the sixteen child routing graphs and are excluded
if they block an existing lower inlet. Query order never participates in those choices.
New basin polygons reserve 1/16 child-span banks on their outer boundary, keeping their surface
away from unrelated transport ports; lake thresholds use the inset polygon's physical area.
Explicit shore-to-receiver spill descriptors remain present below the river display threshold.
The query accepts at most 64 windows and streams intersecting canonical patches depth first,
with no persistent fine cache. A fixed 128 m context crosses wrapped and cube-face boundaries.

New small basins belong to a canonical parent and must lie inside that parent's dry footprint;
their outlets join its prescribed drainage. Larger basins crossing child cells are defined by
the common ancestor, not independently fitted by the children. A basin crossing an export edge
is therefore still one feature.

Ocean geometry has a separate authoritative rule: build a continuous piecewise-linear
below-datum footprint from the backbone samples, clip it to the identified ocean components,
and freeze that polygon geometry. Use the fixed conforming fan triangulation described above and
shared edge intersections/ownership, including cube corners; all distances and surface geometry
are interpreted in world space. Refinement can subdivide its edges but cannot discover straits,
new coastal islands or new ocean connectivity. An isolated fine below-datum depression outside
that footprint is eligible for freshwater, never a new ocean seed. Coarse-representable islands
are retained; coastal islands smaller than the backbone representation remain unresolved. This
choice trades fine coastline discovery for bounded, order-independent ocean identity. Sea bed
conditioning below the common sea datum makes the footprint consistent with fine terrain.

Compute only intersecting canonical cells, their ancestors and bounded geometry influence
neighbours, in sorted order. The full global backbone is bounded; refinement never recursively
follows upstream siblings. A query's detail depth comes from the saved model and physical cell
span, never viewport size or available RAM. A region includes all supported levels intersecting
it; overview selection uses major backbone features. Generating a larger regional rectangle
cannot reveal a different network at common sample positions.

### 5. Condition terrain without making visibility affect it

The existing unconstrained fine relief can obstruct a prescribed coarse river. Painting water
through a mountain is not an acceptable solution. For enabled worlds, make channels/basins a
coordinate-defined terrain constraint, evaluated after regional relief and erosion. Inherited
channel surfaces descend between routing nodes; fill plateaus have equal surfaces and acyclic
rank. Lakes have one horizontal surface at the modelled spill elevation or terminal level.

Within the physical wet footprint (including the authoritative ocean polygon), lower the bed
below the water surface by at least one world height quantum, with a bounded bank transition out to twice the channel width (maximum 128 m).
Ocean and lake bank transitions are likewise bounded to 128 m from their fixed shorelines.
Use an analytic distance/profile field from canonical world geometry; overlapping constraints
combine by minimum bed elevation in a stable order. Basin conditioning similarly guarantees a
submerged bed inside the authoritative footprint. Quantization must leave at least one uint16
step of positive depth; reject unrepresentable configurations before publication rather than
clipping them into dry water pixels. Outside influence footprints terrain is unchanged.

Fine erosion is a pre-conditioning operation. Evaluate the same constraints at overview reference
positions; final regional anchor restoration uses the conditioned reference value. Define every
protected reference value from raw coarse geography plus backbone-only
conditioning, independent of requested refinement depth. Finer-only conditioning tapers to zero
at these known world-lattice positions. When a fine feature is first constructed, treat anchor
clearance circles as routing obstacles: a new river centreline stays at least half its physical
width plus 1 m from an anchor; the entire new lake wet footprint, including its interior,
excludes the closed 1 m neighbourhood of every protected anchor. Inherited
backbone wet geometry is exempt because it already defines the reference value. Use the saved
overview lattice, not whichever image has been generated. Route tributaries around obstacles
with deterministic ties; omit an infeasible new candidate deterministically from the model,
never only from one request. Fine lake candidates with conflicting anchors are similarly
excluded. Record this placement limitation and test a tributary detour; do not let fine wet
pixels at anchors violate positive depth or change the protected reference value.

This changes terrain only for the explicitly enabled new generation model, with independent
streams. `--water none` hides files/overlay but still uses this conditioned terrain. Selection
thresholds or symbolic widths in an overview must not feed back into terrain conditioning.
Keep preview.png in regional output terrain-derived; the overview water overlay has its own file.

### 6. Export interfaces and products

Extend existing Make-accessible commands; no second workflow or UI is needed:

```sh
make world-create PROJECT=out/world ARGS="--seed 42 --geometry sphere --geography world --radius-m 6371000 --hydrology hierarchical"
make world-overview PROJECT=out/world ARGS="--water none"
make world-overview PROJECT=out/world ARGS="--water major"
make region-export PROJECT=out/world ARGS="--x 0 --y 0 --width 512 --height 512 --anchor-lon 0 --anchor-lat 0 --water detailed"
```

These examples extend existing option names and become executable docs/tests. The Python writers
accept keyword-only water mode. `world-overview` defaults to `none`; `region-export` defaults to `auto` (detailed for
enabled worlds, none otherwise), resolved before metadata hashing. Explicit `none` omits water;
`major` is overview-only and `detailed` is region-only. Continue rejecting `exact`, unknown modes
and water requests for disabled worlds before generation or writes. No `coarse` alias is added.

Keep `overview/` and coverage ID `overview` for terrain-only output. Major presentation uses
`overview-major/` and ID `overview-major`, with the same heightmap.png bytes and coordinate
selection, plus water.png, water.json and `water-preview.png` (terrain shading with blue water).
Generalize major river symbols to at least one overview pixel. Categorical overview pixels
represent generalized depiction, not exact fractional physical coverage. Sea and lake precedence
matches detailed output. A second variant never overwrites the first; retrying the same variant
continues to fail through no-overwrite publication. Variant choice is not world identity.

Region outputs retain heightmap.png, heightmap.r16, preview.png, metadata.json and README.md;
detailed mode adds physical-footprint water.png and water.json. Sample categories at canonical
pixel centres, using sea > lake > river precedence. Avoid partition-dependent image-space dilation.
Water.json includes canonical feature IDs, kind, parent ID, connected upstream/downstream IDs,
world-space geometry, physical width, node surface elevations and estimated drainage area; list
only intersecting features, retaining referenced outside-feature IDs and clipping provenance.
The network can be continuous even where a subpixel footprint has no sampled wet pixel.

Metadata records seed, generator/model versions and identity, all parameters, units, geometry,
resolved hierarchy/finest scale, source graph scale, approximation status, category legend,
presentation thresholds and generalization, unresolved detail and `exact_global_drainage=false`.
Separate omitted-by-presentation from unsupported-by-model. Water JSON/geometries use physical
coordinates and SI units, not metre-looking longitude values; spherical positions explicitly use
longitude/latitude degrees while widths/elevations/distances use metres.

Extend the writer's staged publication to both overview variants and every added artifact.
Include JSON, water PNG, overlay and README in coverage hashes. Preserve previous files/index on
write failure, cancellation and interruption, including the existing post-index-commit semantics.
Do not persist timestamps, execution order, absolute paths or timing results in generated artifacts.

### 7. Bound resources and prove the hierarchy before exposing it

Keep existing overview and regional raster/context caps of 1,048,576 samples. Cap backbone cells
at 1,048,576, a request at 65,536 refinement patches and 1,048,576 geometry vertices. Stream or
batch local graph/feature evaluation with a 64 MiB disposable in-memory cache cap; do not retain
all visited patches. Preflight depth and intersecting cell counts arithmetically. While building
bounded pure results, count actual feature complexity and reject excessive work before opening
any output directory. A failure must not leave project state or coverage partly updated.

Before CLI exposure, prove parent budget conservation, no cycles, stable ports, no recursive
upstream expansion, matching physical geometry across sphere faces and positive post-quantization
water depth. Synthetic fixtures must include ocean-free flats, enclosed below-datum basins, a coarse-representable coastal island and seam-crossing coast,
confluences, outlet lakes, a small lake crossing an export edge, inherited river versus fine
mountain relief and a river crossing an overview anchor. A failed invariant blocks delivery;
request-dependent feature removal is not a valid repair.

Use `make water-world-reference` for seed-42 flat bounded, wrap-x and spherical seam/pole examples,
with both overview modes, detailed confluence and small-lake crops, overlays and a suite README.
Choose/record additional deterministic seeds when seed 42 lacks a required feature. Measure peak
RSS, generated patch/vertex counts and wall time outside deterministic data. Publish measurements
and verify complexity on equal-sized requests in small versus planetary extents. Do not claim a
hardware speed target before measuring it; cap violations fail explicitly.

## Risks / Trade-offs

- Procedural drainage differs from exact runoff → label estimates and unresolved scales; reject exact mode.
- Coarse ocean topology misses narrow straits → record backbone scale and inherit its decisions;
  increasing it creates a different world, never patches existing exports.
- Immutable parent paths can look angular; conditioning can carve conspicuous trenches → inspect
  reference maps before acceptance; changing the construction requires a version bump.
- Anchor protection can exclude a small feature near a reference sample → record the constraint,
  test it explicitly and never let output bounds change the result.
- Seam/corner ownership and fixed drainage budgets are the hardest new logic → prove them with
  synthetic graphs before shipping presentation or detailed export support.
- Fixed resource caps reject some requests → actionable errors; no approximate fallback under an exact label.
- This is a larger slice than standalone water → five PR sections; each stops after its PR opens.

## Migration Plan

1. Introduce the validated definition/model and internal backbone, then canonical refinement.
   Until the required conditioning and export tests pass, reject public enabled-world generation
   rather than publishing incomplete terrain with a supposedly finished model version.
2. Ship terrain conditioning with the new schema/generator version before first enabled-world
   publication. Make the pending overview capability explicit until its slice lands.
3. Add major overview variants, then regional detailed products and reference evidence. Every
   slice runs make check and carries a changelog fragment and updated task counts in both roadmaps.
4. Keep standalone output pixel fixtures stable; deliberately update version-bearing metadata
   fixtures. Older saved generator versions continue to fail with the existing actionable error;
   use their recorded generator to resume. Do not add an unrelated compatibility migration.
5. Roll back by using the earlier generator with its own projects or creating a fresh disabled
   project. Do not downgrade/rewrite an enabled project or modify registered exports.
6. Do not archive until the owner accepts the completed reference outputs. Only then synchronize
   specs/archive and update both roadmaps. Biome reconciliation is a separate later change.
