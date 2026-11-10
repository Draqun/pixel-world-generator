# Spec Delta

## Purpose

Keeps contributor change notes complete and publishes versioned, downloadable releases through
a manual process with explicit validation before repository writes.

## ADDED Requirements

### Requirement: Pull requests include change notes
Each pull request SHALL be checked for a new changelog fragment relative to its target branch.
Fragments SHALL support added, changed, fixed and removed categories and English Markdown content.

#### Scenario: Fragment supplied
- **WHEN** a pull request adds a valid fragment
- **THEN** the changelog check succeeds

#### Scenario: Fragment missing
- **WHEN** a pull request adds no fragment
- **THEN** the changelog check fails

#### Scenario: Stacked pull request
- **WHEN** a pull request targets another feature branch
- **THEN** the check compares against that branch rather than main

### Requirement: Releases are manually initiated from main
The release workflow SHALL run only on explicit manual dispatch for main and SHALL use the
version committed in the project. It SHALL reject disagreement with the generator version,
an existing release tag, or failed project checks before publishing repository changes.

#### Scenario: Version disagreement
- **WHEN** the project and generator versions differ
- **THEN** release fails without creating a commit, tag or release

#### Scenario: Existing tag
- **WHEN** the version tag already exists
- **THEN** release fails without moving or overwriting that tag

#### Scenario: Wrong branch
- **WHEN** a release is requested from a branch other than main
- **THEN** no release is published

#### Scenario: Failed validation
- **WHEN** project checks fail
- **THEN** no release commit, tag or release is published

### Requirement: Release publishes the recorded changes and packages
A successful release SHALL consolidate pending fragments into CHANGELOG.md, remove consumed
fragments, and commit those changes to main. It SHALL tag that commit as vX.Y.Z and publish a
GitHub Release with the corresponding notes, wheel and source distribution. Concurrent release
attempts SHALL be serialized and SHALL NOT overwrite newer main commits.

#### Scenario: Successful release
- **WHEN** a maintainer releases a new project version with pending fragments
- **THEN** the changelog and GitHub Release contain the fragment content
- **AND** the tag identifies the changelog commit and both distributions use that version

#### Scenario: Main advances during release
- **WHEN** main advances after the release checkout
- **THEN** publication refuses to overwrite the newer commits

### Requirement: Contributors can preview and verify notes locally
Documented make commands SHALL allow contributors to preview the next changelog and run the
same fragment check locally against a selected target branch.

#### Scenario: Preview
- **WHEN** a contributor previews pending fragments
- **THEN** release notes are displayed without modifying or removing fragments
