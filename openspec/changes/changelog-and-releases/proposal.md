# Proposal

## Why

The repository has no changelog checks or release workflow. Contributors need a small, repeatable
way to record changes and publish versioned downloads without assembling releases by hand.

## What Changes

- Adopt Towncrier fragments and categories from `../sfe-django-engine`.
- Check every pull request for a changelog fragment relative to its actual target branch.
- Add a manually triggered release on `main`, using the committed project version.
- Build the changelog, commit the consumed fragments, and create a version tag and GitHub Release
  with wheel and source distribution downloads.
- Check project/generator version agreement and run project checks before publishing.
- Document local commands and the contributor/release process.

## Capabilities

### New Capabilities

- `release-management`: changelog contribution checks and manual, versioned GitHub releases.

### Modified Capabilities

None. Terrain generation and its deterministic output contract remain unchanged.

## Impact

New GitHub Actions workflows, Towncrier development dependency and configuration, `changelog.d/`,
`CHANGELOG.md`, Make targets and contributor documentation. Release automation needs repository
contents write permission; pull request checks need read permission only. No PyPI publishing,
automatic version bumps, deployment, or numerical dependency changes.
