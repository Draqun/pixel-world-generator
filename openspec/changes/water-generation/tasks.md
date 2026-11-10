# Tasks

Prerequisite: completed terrain-generation. Each numbered section is one PR; open it before
starting the next section. Run make check for each section and add its changelog fragment.

## 1. Sea, retained lakes and routing surface

- [ ] 1.1 Add pure sea connectivity and priority-flood depression handling with stable flat/outlet ordering; verify synthetic bowls, barriers, plateaus, no-sea and all-sea cases, input immutability and absence of drainage cycles.
- [ ] 1.2 Add and validate recorded sea/depth controls, document units and default datum in README.md, and bump both version declarations with intentional golden updates; verify non-finite/out-of-range inputs are rejected and existing terrain byte hashes stay unchanged.

## 2. Catchments and river geometry

- [ ] 2.1 Add exact D8 contributing-area accumulation, thresholded river centrelines and bounded widening; verify branching catchments, flat routing, outlet reachability, width ordering, category precedence and empty river output.
- [ ] 2.2 Document the channel approximation and record reference timings/peak memory for 1024 and 2048 through a Make target; verify a seed-42 preview by inspection and retain exact catchment tests without replacing them with bounded erosion sweeps.

## 3. Layer outputs and CLI integration

- [ ] 3.1 Integrate water.png, metadata legends, CLI controls and Make ARGS forwarding, moving serialization into one writer while retaining current CLI callers; verify the four existing outputs remain present and height PNG/R16/preview bytes stay identical for unchanged terrain parameters.
- [ ] 3.2 Extend the all-file SHA-256 determinism test and golden fixtures, document Make usage and water categories; verify two seeds, same seed twice, water-only parameter isolation, invalid input before output creation and make check.

## Workflow follow-up

- After the final PR and owner visual confirmation, synchronize surface-water and archive this change.
- Biome-generation may begin only after this change's implementation is merged.
