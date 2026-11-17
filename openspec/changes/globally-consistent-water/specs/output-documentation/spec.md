# Output documentation delta

## MODIFIED Requirements

### Requirement: Guides explain physical interpretation
Image-output guides SHALL explain dark-to-low and light-to-high grayscale, image dimensions,
coordinate direction, horizontal scale and vertical decoding from saved parameters. Overview
guides SHALL distinguish coarse projection-dependent sampling from one-metre regional pixels.
Guides SHALL state which layers are available or omitted, using the output's recorded contract.

#### Scenario: Coarse world overview
- **WHEN** a world overview is exported
- **THEN** its README explains the saved geometry, projection and physical extent
- **AND** does not describe overview pixels as one metre or sea-datum shading as a river network

#### Scenario: Regional terrain
- **WHEN** a region is exported
- **THEN** its README states its grid location, projection where applicable and one-metre sampling
- **AND** explains shared vertical encoding and points to metadata for projection limits
- **AND** describes included water layers and explicitly identifies every omitted layer

#### Scenario: Hydrology-enabled output
- **WHEN** an overview or region includes world-linked water
- **THEN** its guide explains the categorical legend, water.json, model identity and physical scales
- **AND** distinguishes major-only display, detailed procedural coverage and unresolved smaller water
- **AND** identifies symbolic overview widths, terrain conditioning and unavailable exact drainage

#### Scenario: Hidden water
- **WHEN** an enabled world is exported without a water layer
- **THEN** its guide explains that water is omitted from this presentation rather than absent from the world
- **AND** does not describe sea-datum terrain shading as a water network
