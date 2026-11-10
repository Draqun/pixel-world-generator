# Changelog fragments

Each PR adds `<issue>.<type>.md`, for example `12.fixed.md`.
Types: `added`, `changed`, `fixed`, `removed`. Write one entry in English.
Without an issue, use `+short-name.added.md`. Use a unique name per change.

Preview: `make changelog-draft`. Check: `make changelog-check TARGET_BRANCH=main`.
Do not edit generated `CHANGELOG.md` entries by hand. See README.md for releases.
