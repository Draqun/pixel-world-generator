# World hydrology implementation status

The first two slices provide an internal, bounded global backbone and canonical local refinement. It does not export world water,
condition terrain or enable `--hydrology` on the CLI. Existing world projects, overviews and
regional terrain keep their existing formats and bytes. Standalone water is unchanged.

The next slices add water-compatible terrain, optional major-water
world overviews and detailed regional water. See the
[tracked tasks](../openspec/changes/globally-consistent-water/tasks.md).

## Definition and publication boundary

`pixel_world.world_water.HydrologyDefinition` is immutable. Its default model is `none`;
`hierarchical-v1` enables internal backbone and refinement calculation. Its canonical dictionary includes all
settings and versioned constants. Loading a dictionary rejects missing/unknown fields, invalid
units/ranges, unsupported model versions and altered constants. Model identity hashes this full
definition together with the immutable world definition; coverage, file paths and display mode
are excluded.

The hydrology definition can round-trip in memory, but is not yet added to saved `world.json`.
Schema 3, enabled-world persistence, generator-version changes and CLI selection belong to the
terrain-conditioning slice. The writer explicitly refuses enabled project creation before
creating a parent directory or touching an existing project. Disabled project creation is
byte-compatible, including when passed an explicit disabled hydrology definition.

No generated hydrology snapshot is advertised as a stable public output format. The internal
snapshot exists for repeatability checks and records its format, model/world identities,
parameters, geometry units, routing, estimated areas, feature IDs and authoritative ocean facets.
Generation functions do no I/O.

## Global topology and physical area

The default backbone has 64 cells along a flat world's longest axis or each of six sphere faces.
Flat grids preserve physical aspect ratio and wrap only x when configured. Wrapped grids have
at least two x cells. Only real outer edges are drainage outlets; neither cube-face boundaries
nor export edges create outlets.

Every quadrilateral cell owns one routing site at its centre, its physical local source area
and at most one downstream cell/outlet. Each has four canonical edge-midpoint ports. Routing
and local budgets are not assigned to shared geometry vertices. This representation is directly
used as the parent of a 4 by 4 refinement patch; incoming flux crosses its shared ports.

Integer cube coordinates identify shared sphere edges and corners exactly, using the same
x-before-y-before-z ownership order as the existing atlas. The sphere has `6*n*n` parent cells
for face resolution `n`. Each cell's area is the sum of two spherical-triangle areas, not an
image-pixel area. Those areas sum to the sphere surface area, and accumulated source areas are
conserved up to floating-point roundoff. Their interpretation as fine-terrain catchments remains
approximate. Across wrapped edges, geometric triangles retain local unwrapped coordinates.

Shoreline geometry is separate: each quad has eight conforming triangles joining its centre,
edge midpoints and corners. Shared edge heights average the adjacent source-cell elevations;
corner heights take their maximum. This conservative corner rule prevents diagonal low cells
from inventing an ocean connection across an intervening dry cell. It is a recorded coarse
interpolation convention, not a promise to recover fine coastlines. Shared points are owned once
across face seams, and poles are covered by the same geometry.

## Oceans, lakes and rivers

Below-datum connectivity uses the complete graph. In bounded flat worlds, only low components
connected to real world boundaries seed ocean. Wrapped worlds first consider their real north
and south boundaries. If a wrapped world has no such ocean, or for spheres, the largest low
component by physical area becomes the model ocean; ties use the smallest canonical cell ID.
Other enclosed low components are basins. If no sample is below datum, ocean is absent.

Priority-flood begins at ocean sites and actual world outlets. A closed ocean-free sphere uses
its lowest cell as an identified terminal basin root, with canonical-ID tie-breaking. Routes
are acyclic and water surfaces do not rise downstream. Retained depressions share a surface and
one deterministic spill connection; changing routes within a lake recalculates ranks and
accumulation. A terminal basin root is not automatically an invented positive-depth lake.

Lake selection uses recorded minimum area and maximum retained depth, retaining the connected
wet footprint when it qualifies. River selection uses model-estimated accumulated square metres.
Width is `min(max_channel_width_m, max(1, sqrt(area_m2 / 1_000_000)))` metres.
River geometry passes through the canonical shared outlet port; world outlets extend to the
actual world boundary rather than stopping at the edge cell centre. Stable IDs identify
rivers, lakes, ocean components, terminal basins and true world outlets. Downstream references
skip dry, subthreshold channel sites and still resolve to another feature or a true root.

Ocean geometry is fixed by clipping the backbone triangles at the sea datum and retaining only
the selected ocean components. Shared intersections use one arithmetic direction per edge.
Future regional materialization consumes these facets; it cannot infer a new ocean connection
from local elevations. Coarse islands remain dry, but sub-backbone straits and coastal islands
are unresolved. Sea-bed conditioning is still required before these facets can be exported
with regional terrain.

## Canonical refinement and shared geometry

`pixel_world.water_refinement` refines a complete parent into sixteen children, regardless of
export rectangles. Cell IDs contain the face, depth and global grid indices. Exact rational
flat coordinates and primitive integer cube vectors identify ports across levels, wrapped
edges and spherical seams. Each shared port carries one position, surface elevation and
model-estimated drainage area.

A patch subdivides only its parent's local physical source area, with a residual correction.
Imported area enters exactly once at its canonical owning child. Child accumulation replaces
the coarse allocation; it never adds that allocation again. All children drain through an
acyclic graph to the prescribed parent outlet. No upstream fine patch is evaluated.

Parent-keyed routing uses the existing coordinate terrain as a suitability field. Published
river geometry, widths and profiles remain immutable. Orthogonal child channel paths pass
through their transport ports and stop at the first physical receiver. A candidate is excluded
if that contact would create a lower sink than the containing child's prescribed outlet; it
cannot divert the parent drainage budget into incidental water. Prescribed low inlets
receive constrained routes around higher inherited carriers. Boundary-only channels constrain
transport only when an incoming port carries their profile; an incidental boundary crossing is
not an additional inlet. Sea and lake planes determine the wet surface where they cover a
river curve. Ordinary child interfaces crossing an active inherited
carrier use that curve's surface; upstream potentials accommodate the shared datum without
changing the carrier's exact locked ports. The coarse snapshot remains unchanged.

New channel geometry records the prescribed datum at every transport point it crosses,
including bends coinciding with an inlet. A low inlet may reach the exact parent outlet at a
shared corner instead of crossing a higher edge midpoint. Before accepting a new carrier,
check that it preserves access from the known inlets of every affected child. This uses at
most sixteen fixed-size routing graphs; it generates no finer terrain or geometry. Conflicting
candidates are excluded deterministically.

New tributaries use the same physical-area thresholds and width rule as the backbone. New
lakes belong to a common canonical parent, share one surface and retain a physical spill path,
even when its river symbol is below threshold. Coarse lakes gain explicit outlet descriptors
without changing their original records. New lake polygons reserve a dry bank of 1/16 of a
child span along their outer boundary, avoiding unrelated transport ports; their thresholds
use the actual polygon area. They exclude inherited water footprints and channel widths.
The same feature ID, complete geometry and profile are returned across crops and query order.
Features below the saved finest scale remain unresolved; this is procedural drainage, not an
exact solution of the eventual metre-resolution heightmap.

The internal query takes face-grid windows in coarse-cell units. It expands them by a fixed
128 m context, splits wrapped windows and maps spherical edge/corner context onto adjacent
faces. It returns complete ancestor-owned features touching the canonical working patches;
regional raster clipping and terrain conditioning are pending later slices.

## Determinism and resource limits

The coarse heights use the existing `world.geography` stream; routing and topology consume no
random numbers. Drawing from the independent `world.water.backbone`, `world.water.refinement`
or `world.water.basins` namespaces cannot change the backbone. Refinement uses
`world.water.refinement:<canonical-parent-id>` rather than query order. No global
random state or unordered traversal decides results.

Preflight arithmetic caps backbone cells and supporting geometry vertices at 1,048,576 each before mesh allocation.
It rejects worlds that cannot reach the configured finest span (default 64 m) with at most 16
fourfold refinements, unrepresentable physical area and vertical encoding that cannot leave a
submerged height quantum below sea. Ocean and feature geometry share an aggregate 1,048,576-vertex limit checked
while building pure results, before any publication. Work scales with the bounded coarse graph,
never a metre-resolution world raster. Queries accept at most 64 windows. Arithmetic preflight
counts the union of intersecting canonical patches and ancestors, rejecting more than 65,536
patches before terrain sampling. Geometry, including spill descriptors, has an aggregate
1,048,576-vertex cap. Depth-first evaluation holds only the ancestor stack (at most the saved
depth), returns bounded geometry and retains no fine cache. Work does not expand into fine
upstream catchments; excessive requests fail instead of silently reducing detail.

Run the focused regression checks through the existing target:

```sh
make test ARGS="tests/test_world_water.py tests/test_water_refinement.py"
```

Tests cover definition round trips, no-write rejection, shared geometry, physical area, ocean-free
and enclosed-basin cases, lake spill ownership, root flux conservation, stable feature connections,
allocation preflight, local/imported area conservation, deep profile constraints, cropped and
seam-crossing queries, bounded work and repeated serialized output hashes. These checks do not establish visual
quality, exact fine-terrain drainage or production performance.
