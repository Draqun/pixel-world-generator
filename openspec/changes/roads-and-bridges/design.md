# Design

## Context

Requires merged settlement-generation with stable settlement IDs, water classes and unquantized
slope fields. No reusable pathfinder exists in this repo. Output stays data rather than Godot code.

## Goals / Non-Goals

**Goals:** a connected network wherever the traversal rules permit, with honest disconnections.
**Non-Goals:** optimal road engineering, terrain deformation, urban streets, ferries or tunnels.

## Decisions

- Proposed `roads.py` constructs an eight-neighbour dry-land traversal graph; slope above a
  default 30 degrees is blocked. Dry cost is step length times `1 + 4 * slope_degrees / 90`,
  with a fixed documented wetland surcharge. The cost is nonnegative and monotonic in slope.
  Diagonal land moves require both orthogonal neighbours to be traversable.
- Add bridge edges by scanning cardinal directions across contiguous lake/river cells to safe
  dry banks, bounded by default maximum span 32 m (0 disables bridges). Crossing cost is span
  length times a recorded default multiplier 8. Sea blocks crossings. Cardinal spans are an
  explicit initial bridge policy, not a claim to find arbitrary-angle engineering solutions.
- A* uses straight-line distance as an admissible heuristic, heapq and fixed row-major ties.
  Reuse the same graph rules for reachability tests. Keep pure graph/routing code separate from
  serialization; no global RNG is needed, but any later randomized choice requires its own stream.
- Consider all settlement pairs in stable increasing Euclidean distance/ID order. Use union-find
  to skip already joined pairs, trying A* for remaining pairs and adding successful connections.
  This yields a spanning forest, including fallback pairs when a preferred edge is blocked.
  Do not call a nearest-neighbour heuristic's failure a physical disconnection.
- Deduplicate identical bridge spans by canonical endpoint order. Stable road records contain
  endpoint IDs, ordered `[x,y]` path and bridge IDs. roads.json also lists component settlement
  IDs. bridges.json records crossing paths and bank endpoints. Rasterize only one-pixel centrelines;
  roads.png codes are 0 none, 1 dry road, 2 bridge. Shared cells and entities stay consistent.
- Add slope/crossing controls to Params and CLI, record costs and legends, bump generator version.
  Route controls cannot modify upstream arrays, entities or random draws.

## Risks / Trade-offs

- [Pairwise routing on a large map is expensive] → Bound paths by the map and use union-find
  to avoid redundant searches. Benchmark default settlement counts at 1024; do not promise a
  globally minimum-cost road network or introduce a coarse-grid route that misses valid paths.
- [River display width differs from centreline] → Use the actual categorical mask for bank/span
  checks; tests include confluences, wide lakes, sea and diagonal corner obstacles.
- [Some islands remain unreachable] → Export components and isolated settlement IDs explicitly.

## Migration Plan

Implement the traversal graph/bridges, then the network, then output integration as separate PRs.
Wait for settlement-generation; preserve every upstream hash throughout.
