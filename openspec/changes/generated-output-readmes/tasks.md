# Tasks

One numbered section is one implementation PR. Include its tests, documentation and changelog;
run `make check` and open the PR before stopping.

## 1. Generated output guides

- [ ] 1.1 Add deterministic English README rendering and writing for standalone maps, project roots,
  overviews and regions in the writer. Verify file descriptions, dimensions, grayscale, datum,
  flat/spherical scale and omitted layers against output metadata using focused writer/CLI tests.
- [ ] 1.2 Include README in area hashing/publication, project-creation cleanup and interactive
  overwrite detection. Verify failure during README writing leaves no incomplete coverage or
  damaged previous files, README-only destinations prompt, and older projects without guides load.
- [ ] 1.3 Add suite entry-point guides to both reference scripts with relative project/image links,
  fixture explanations and descriptions of checks and suite files. Run both Make reference targets
  into fresh destinations, check every emitted link and inspect a regional suite guide manually.
- [ ] 1.4 Update exact output assertions and aggregate goldens; compare all README hashes across
  identical fresh runs and old data bytes against pre-change baselines. Verify adding neighbours
  or a later overview leaves existing guides unchanged and export order remains irrelevant.
- [ ] 1.5 Document generated guides in repository README, update the roadmap and add a changelog
  fragment. Run `make check`, review the diff and open the single slice PR.

## Workflow follow-up

- After owner confirmation that the guides explain the generated files, synchronize
  output-documentation and archive in the last PR.
