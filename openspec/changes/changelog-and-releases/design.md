# Design

## Context

The project has no Actions workflows, changelog or release tooling. Versions are duplicated in
`pyproject.toml` and `src/pixel_world/__init__.py`, both currently 0.1.0. Hatchling already builds
the package; uv and Make are the existing command interfaces. See proposal.md for motivation.
The reference project uses Towncrier with four categories and a manual release job.

## Goals / Non-Goals

**Goals:** reuse that contributor model with small GitHub-native workflows and no extra secrets.

**Non-Goals:** automatic version selection, PyPI, deployment, branch protection administration,
or reconstructing historical notes. Wheel and sdist attachments are an implementation assumption
made during planning, not an explicit owner requirement.

## Decisions

### Towncrier with Make entry points

Add Towncrier as a development dependency, configured for `changelog.d/`, Markdown output and
added/changed/fixed/removed types. Match the reference naming scheme, including issue-less
`+short-name.fixed.md` fragments. Add changelog-check, changelog-draft and changelog-build targets.
Seed CHANGELOG.md with its insertion marker and add a fragment for this automation.
Use Towncrier rather than a custom fragment parser or commit-derived release notes, so entries
remain contributor-written and match the reference project.

### Pull request check with read-only permissions

Use pull_request, checkout with full history, Python 3.13 and locked uv dependencies.
Compare with the actual base branch, supplied through an environment variable and quoted in
shell commands; do not interpolate branch names into executable shell text. Run the Make check
target. No arbitrary commit-message bypass or pull_request_target execution.

### Manual release with the built-in token

Use workflow_dispatch, main-only execution, contents: write and a single concurrency group
without cancellation. Check out main with full history. Validate versions, check tag absence,
require pending fragments and run make check before changing tracked files. The committed
project version is authoritative; maintainers update both version declarations before release.
This preserves intentional generator version changes rather than guessing a bump from fragments.

Capture Towncrier's draft notes, build the changelog, build distributions with uv, and commit
only CHANGELOG.md and changelog.d/. Create vX.Y.Z on that commit. Push main and the tag atomically
without force, then publish with gh release create --verify-tag and attach dist files. Shell
steps fail on errors. The built-in GITHUB_TOKEN avoids a new long-lived credential. Use Make
targets for local release preparation/build commands and documentation.

### Scope and verification

Implement one tasks section / PR. Touch workflow YAML, pyproject.toml, uv.lock, Makefile,
changelog files and README.md; add a small release-validation helper and focused tests only if
the workflow cannot express the validation clearly with existing commands. No generation
algorithm or version bump belongs to this tooling change. Verify workflows with actionlint,
fragment acceptance/rejection in a temporary repository, changelog build in a disposable copy,
distribution contents/version, and make check. Do not create a real release during validation.

## Risks / Trade-offs

- [Protected main rejects automation writes] → Document that release requires token write access
  and branch rules permitting the release commit; do not silently bypass protections.
- [GitHub Release creation fails after the atomic push] → Preserve the existing tag; document
  completion using gh release create --verify-tag for that exact tag. A rerun must not retag.
- [Main advances during preparation] → Atomic non-force push rejects stale publication.
- [GITHUB_TOKEN pushes do not start ordinary push workflows] → Run checks and build artifacts
  inside the release workflow rather than depending on a later tag workflow.
- [A failing check does not itself prevent merging] → Describe the check name for optional
  branch protection configuration; changing repository rules is outside this slice.

## Migration Plan

Merge the workflow/configuration PR before the first manual dispatch. Add fragments to later
PRs and bump both committed versions intentionally when preparing a new release. Roll back by
reverting the tooling PR; keep any already published tags/releases intact.
