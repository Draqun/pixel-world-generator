# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository. Claude Code loads this file
through `CLAUDE.md`.

## Project

`pixel-world-generator` is a standalone, seeded world map generator. One pixel is one metre. It
builds terrain (16-bit heightmap), water (lakes, rivers, sea), biomes, then settlements, roads,
bridges and borders. It is a separate tool; the game that may consume its output is
`/home/damian/selflearning/retro-game` (Godot 4). Output is data (PNG layers + JSON), never game code.

Planned slices (see `README.md`): terrain, water, biomes, settlements, roads and bridges, borders.
Build them in this order; each depends on the previous one.

## Language

- English everywhere: code, comments, commit messages, docs, OpenSpec artifacts, issues and PRs.
- Conversations with the owner are in Polish.

## Workflow (OpenSpec)

- Every feature starts with a spec: `/opsx:propose` (or the `openspec-propose` skill). Specs live in
  `openspec/`; keywords (`SHALL`/`MUST`, `WHEN`/`THEN`, `### Requirement:`) stay as OpenSpec defines them.
- Deliver in small slices: one `tasks.md` section per PR. Do only the tasks of the slice, tick them,
  run `make check`, open the PR, stop. Never start the next slice before the PR is open.
- Run the OpenSpec CLI with `OPENSPEC_TELEMETRY=0` (the `Makefile` sets it).
- Archive a change (`openspec archive <change>`) only in its last PR, after the owner confirmed it works.

## Determinism rules (binding)

- **Same seed + same generator version + same parameters = byte-identical output.** A test must
  generate twice and compare file hashes.
- One independent random stream per generation step, derived from the master seed and the step name
  (e.g. `numpy.random.SeedSequence` spawned by a stable key). Changing one step must not change
  another step's output.
- Never use the global `random` / `numpy.random` module state. Never depend on set or dict iteration
  order for results.
- Pin numerical dependencies by exact version in `pyproject.toml`. Floating point is only guaranteed
  on the same platform; if a map is shared, ship the generated data, not the seed.
- Every output records `seed`, `generator_version` and all parameters in a JSON metadata file. A
  change to the algorithm bumps the generator version.

## Output format

- Heightmap: 16-bit single-channel PNG. 8-bit is forbidden (visible terracing).
- Other layers (water, biome, slope, roads, borders): separate PNGs, same size as the heightmap.
- Entities (towns, villages, fortresses, bridges, borders): JSON.
- Layout is x right, y down, pixel (0, 0) top left, so a layer overlays the heightmap 1:1.

## Code rules

- Python 3.13, `uv`, `numpy`. Type hints on all public functions. `ruff` clean.
- Each generation step is a pure function: arrays and a seeded `numpy.random.Generator` in, arrays
  out. No I/O inside steps; I/O lives in one writer module and the CLI.
- No new dependency for a few lines of code. Algorithms (noise, erosion, priority-flood, A*) are
  written here and covered by tests.
- Tools and scripts go through `make` targets; docs show `make` commands.

## Before you push

- Run `make check` (lint, tests, `openspec validate --all --strict`).
- Keep each PR focused on one slice.

## VCS

- Colocated Jujutsu repo (`.jj` + `.git`). One change per logical piece; use `jj commit -m "..."`
  rather than `jj describe`. After `jj git push` run `jj new`.
- Commit messages: `<type>(<scope>): <subject>`, imperative, first line at most 72 characters.
- `.claude/` (OpenSpec skills and `/opsx:*` commands from `openspec init`) is gitignored: never
  commit it. `openspec/` is committed.
