# Proposal

## Why

The existing command requires users to remember options and find generated images manually. An interactive terminal interface can make configuring, generating and inspecting a world approachable while keeping scripted generation available.

## What Changes

- Introduce a Typer command and Textual terminal form for configuring generation and inspecting generated layers with keyboard or mouse.
- Provide previews both inside the terminal and in the system image viewer, with useful fallbacks when unavailable.
- Make parameter selection and repeated generation easy, with all interactive generation settings also available through non-interactive flags.
- Preserve the existing non-interactive generate command, output formats and determinism guarantees.
- Expose only implemented stages and layers; extend the menu as those stages are integrated separately.

## Capabilities

### New Capabilities

- `interactive-world-cli`: Interactive navigation, generation configuration and preview of available world output.

### Modified Capabilities

None.

## Impact

CLI entry point, Make targets, documentation, CLI tests and Python dependencies. Water output integration is in a separate in-progress change; integration must target the actual merged state. No generator algorithm or output format changes are intended.
