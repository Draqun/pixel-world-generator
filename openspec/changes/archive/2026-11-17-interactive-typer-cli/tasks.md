# Tasks

Each numbered section is one PR. Run make check and add a changelog fragment before opening the PR. Reconcile with the current water CLI integration before implementation.

## 1. Interactive world CLI

- [x] 1.1 Add Typer and migrate command dispatch while retaining existing `main(argv)`, `generate(params, out)`, options and exit behavior; expose every interactive generation setting as a flag and verify CLI tests, invalid inputs and unchanged file hashes.
- [x] 1.2 Add keyboard menu and individually editable configuration with explicit seed, values, defaults, descriptions, ranges, retained settings, validation, cancellation and overwrite confirmation; test repeat runs, invalid values, cancellation, file protection and non-terminal invocation.
- [x] 1.3 Add available-image selection with bounded terminal preview and system viewer launch, including monochrome and failure recovery; test both preview paths, terminal sizing, missing images and unavailable viewers, and confirm unsupported stages are not offered.
- [x] 1.4 Add a Make target, README usage and changelog fragment; verify documented interactive and flag commands, inspect both preview modes, compare interactive and scripted output hashes and run make check.

## Workflow follow-up

- Archive only in the last PR after the owner confirms the interface works.
