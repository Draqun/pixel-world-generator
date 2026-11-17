# Spec Delta

## Purpose

Provide an approachable terminal workflow for configuring and inspecting generated worlds while retaining scriptable generation.

## ADDED Requirements

### Requirement: Interactive menu
The application SHALL provide an explicit interactive entry point with a readable form navigable by keyboard and mouse, offering editable values, a size selector, generation, output inspection and exit.

#### Scenario: Start and exit
- **WHEN** the user starts the interactive interface in a terminal
- **THEN** available controls, values and instructions are displayed
- **AND** the user can return to the menu or exit without generating files

#### Scenario: Non-interactive input
- **WHEN** interactive mode is invoked without an interactive terminal
- **THEN** it exits promptly with an actionable message and writes no files

### Requirement: Configure a generation
The interactive interface SHALL let the user set the seed, output directory and generation parameters, show current values, defaults, descriptions and valid ranges, and validate them before writing.

#### Scenario: Generate with selected values
- **WHEN** the user supplies a valid integer seed and parameters and confirms generation
- **THEN** the world is generated in the selected output directory
- **AND** its metadata records the selected seed and parameters

#### Scenario: Invalid value or cancellation
- **WHEN** a value is invalid or the user cancels before generation
- **THEN** no output files are written and the user can correct the value or return to the menu

#### Scenario: Refine a generated world
- **WHEN** the user returns to configuration after generating a world
- **THEN** the previous values remain available and individual parameters can be changed before another run

### Requirement: Protect existing output
The interactive interface SHALL ask for confirmation before overwriting any existing generated output files and SHALL preserve them if the user declines.

#### Scenario: Decline overwrite
- **WHEN** generation would overwrite an existing output file and the user declines confirmation
- **THEN** existing files remain unchanged and generation is not started

### Requirement: Inspect generated output
The interactive interface SHALL list available generated image layers in the selected output directory and let the user preview a selected layer in the terminal or open it in the system image viewer.

#### Scenario: Terminal preview
- **WHEN** the user chooses a terminal preview of an available image
- **THEN** a scaled representation is displayed within the terminal dimensions
- **AND** the user can return to the menu

#### Scenario: Open external preview
- **WHEN** the user selects an existing preview image
- **AND** chooses the system viewer
- **THEN** the application requests that the system open that image and remains usable

#### Scenario: Preview unavailable
- **WHEN** no image exists or the chosen preview method is unavailable
- **THEN** the interface explains the problem, displays the relevant path and returns to the menu

### Requirement: Available stages only
The menu SHALL offer only generation actions and layers implemented in the running application; it SHALL NOT imply that planned stages can already be generated.

#### Scenario: Future stage unavailable
- **WHEN** a generation stage has not been implemented
- **THEN** the menu does not offer it as a runnable action

### Requirement: Preserve scripted generation
The existing non-interactive generate invocation and its options SHALL continue to work without prompts and preserve its exit behavior, validation and generated output bytes for the same inputs. Every generation setting available interactively SHALL also be configurable through command-line options.

#### Scenario: Existing script
- **WHEN** an existing valid generate command is run
- **THEN** it produces the same files and bytes as before for the same seed, version and parameters
- **AND** it does not prompt for input

#### Scenario: Equivalent interactive and flag settings
- **WHEN** a world is generated using command-line options equivalent to interactive settings
- **THEN** both runs use the same validation and produce byte-identical output files on the same platform
- **AND** the command-line run requires no interaction
