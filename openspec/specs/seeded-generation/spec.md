# seeded-generation Specification

## Purpose

Makes every generated world reproducible from a seed, records exactly what produced it, and gives
the tool a command-line entry point. Later generation steps rely on these guarantees.

## Requirements

### Requirement: Seed is required
The generator SHALL require an integer seed and SHALL NOT draw randomness from any other source.

#### Scenario: Seed given
- **WHEN** the user runs the generator with `--seed 42`
- **THEN** generation succeeds and the metadata records seed 42

#### Scenario: Seed missing
- **WHEN** the user runs the generator without `--seed`
- **THEN** it exits with a non-zero status and a message naming the missing seed
- **AND** it writes no output files

#### Scenario: Seed not an integer
- **WHEN** the user passes `--seed abc`
- **THEN** it exits with a non-zero status and writes no output files

### Requirement: Output is reproducible
For the same seed, generator version and parameters, the generator SHALL produce byte-identical
output files on the same platform.

#### Scenario: Same seed twice
- **WHEN** the generator runs twice with the same seed and parameters into two directories
- **THEN** the heightmap, preview and metadata files are byte-identical between the directories

#### Scenario: Different seeds
- **WHEN** the generator runs with seed 1 and with seed 2 and the same parameters
- **THEN** the two heightmap files differ

### Requirement: Generation steps use independent random streams
Each generation step SHALL draw from its own random stream, derived only from the master seed and
the step's name, so that changing one step does not change another step's random input.

#### Scenario: Erosion parameters change
- **WHEN** only the erosion parameters change between two runs with the same seed
- **THEN** the noise field before erosion is identical in both runs

#### Scenario: Stream depends on step name
- **WHEN** two different steps derive their streams from the same seed
- **THEN** the streams produce different sequences

### Requirement: Metadata records the run
The generator SHALL write a JSON metadata file holding the seed, the generator version and every
parameter used, with no timestamps, host names or other run-specific values.

#### Scenario: Metadata contents
- **WHEN** a run finishes
- **THEN** the metadata file contains `seed`, `generator_version` and all generation parameters,
  including the ones left at their defaults

#### Scenario: Metadata is stable
- **WHEN** the same run is repeated
- **THEN** the metadata file is byte-identical

### Requirement: Parameters are validated
The generator SHALL reject invalid parameters before doing any work.

#### Scenario: Size out of range
- **WHEN** the user passes a `--size` smaller than 64 or larger than 8192
- **THEN** it exits with a non-zero status naming the allowed range and writes no output files

### Requirement: Output location
The generator SHALL write its files into the directory given by `--out`, creating it when missing,
using fixed file names.

#### Scenario: Default files
- **WHEN** a run finishes
- **THEN** the output directory contains `heightmap.png`, `heightmap.r16`, `preview.png` and
  `metadata.json`

#### Scenario: Directory missing
- **WHEN** `--out` names a directory that does not exist
- **THEN** the directory is created and the files are written into it
