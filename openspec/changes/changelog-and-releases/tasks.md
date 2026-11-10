# Tasks

## 1. Changelog checks and manual GitHub releases

- [x] 1.1 Add Towncrier to development dependencies and the lockfile, configure the four fragment categories, seed CHANGELOG.md and document fragment naming in changelog.d/README.md; verify locked installation and a draft containing this change's fragment.
- [x] 1.2 Add Make targets for changelog preview, build and comparison, plus the pull request workflow using the actual base branch; verify fragment acceptance and rejection in a temporary repository (including a feature-branch base) and run actionlint.
- [x] 1.3 Add the main-only manual release workflow, version/tag checks, serialized execution, project checks, package build, changelog commit, atomic non-force branch/tag push and GitHub Release creation; verify version mismatch and existing-tag rejection with a focused self-check or tests, and prepare a full release in a disposable copy without publishing.
- [x] 1.4 Document contributor and release commands, permissions, intentional version bumps and recovery after a failed GitHub Release API call in README.md; verify documented local commands, wheel/sdist versions and contents, actionlint and make check.

## Workflow follow-up

- Open one PR for this section and stop before starting other feature work.
- After merge, verify the changelog workflow on GitHub; run the first real release only when requested.
- Sync and archive this change after the owner confirms the workflows work.
