# Tasks

Prerequisite: settlement-generation merged. Each numbered section is one PR; open it before the
next. Run make check and add a changelog fragment for each section.

## 1. Terrain traversal and valid bridge edges

- [ ] 1.1 Add pure dry-land costs and bounded cardinal bridge-edge discovery; verify slope monotonicity, impassable slopes, blocked corners, safe banks, maximum spans, disabled bridges, sea rejection and shared-span canonicalization.
- [ ] 1.2 Add validated route/crossing controls, document graph policy and units in README.md and bump both versions; verify non-finite and invalid limits, upstream hash preservation and intentional golden changes.

## 2. Paths and spanning forest

- [ ] 2.1 Add deterministic A* and pairwise/union-find network assembly; verify exact shortest paths on tiny graphs, fallback pairs, disconnected islands, equal-cost ties and zero/one settlement cases.
- [ ] 2.2 Document disconnected-component semantics and benchmark the default 1024 map through Make; verify every reachable settlement component is connected according to the same graph rules and inspect reference road/bridge geometry.

## 3. Raster and entity outputs

- [ ] 3.1 Integrate roads.png, roads.json and bridges.json with stable IDs and references; verify raster/JSON agreement, bank endpoints, shared bridge deduplication, ordered paths and component lists.
- [ ] 3.2 Extend all-output SHA-256 and golden tests, document Make usage and metadata legends; verify route-only control changes preserve all upstream files, repeated generation matches byte-for-byte and make check passes.

## Workflow follow-up

- After the final PR and owner visual confirmation, synchronize transport-network and archive.
- Border-generation may begin after this implementation is merged.
