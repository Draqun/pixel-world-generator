"""Immutable world definitions and coordinate conventions, independent of raster coverage."""

import hashlib
import json
import math
from dataclasses import asdict, dataclass

from pixel_world import __version__


def finite(value: float, name: str) -> None:
    """Reject nonnumeric, nonfinite and boolean values at the public boundary."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be a finite number")


def canonical_json(value: object) -> bytes:
    """Stable UTF-8 bytes for project files and content identities."""
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


@dataclass(frozen=True)
class WorldDefinition:
    seed: int
    geometry: str
    geography: str
    width_m: float | None = None
    height_m: float | None = None
    radius_m: float | None = None
    boundary: str = "bounded"
    height_min_m: float = 0.0
    height_range_m: float = 400.0
    sea_level_m: float = 80.0
    overview_resolution: int = 512
    parameters: tuple[tuple[str, int | float], ...] = ()
    schema_version: int = 1
    coordinate_version: int = 1
    generator_version: str = __version__

    def __post_init__(self) -> None:
        for name in ("schema_version", "coordinate_version"):
            if type(getattr(self, name)) is not int or getattr(self, name) != 1:
                raise ValueError(f"unsupported {name}; use a compatible generator")
        if self.generator_version != __version__:
            raise ValueError("unsupported generator_version; use the project's recorded generator")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")
        if self.geometry not in ("flat", "sphere"):
            raise ValueError("geometry must be flat or sphere")
        if self.geography not in ("region", "island", "peninsula", "continent", "world"):
            raise ValueError("unsupported geography")
        if self.boundary not in ("bounded", "wrap_x"):
            raise ValueError("boundary must be bounded or wrap_x")
        if self.geometry == "flat":
            if self.radius_m is not None:
                raise ValueError("flat worlds cannot have a radius")
            dimensions = ("width_m", "height_m")
        else:
            if self.width_m is not None or self.height_m is not None or self.boundary != "bounded":
                raise ValueError("spheres use radius_m, not planar dimensions or boundary flags")
            dimensions = ("radius_m",)
        for name in dimensions:
            value = getattr(self, name)
            finite(value, name)
            if value <= 0:
                raise ValueError(f"{name} must be positive")
            object.__setattr__(self, name, float(value))
        for name in ("height_min_m", "height_range_m", "sea_level_m"):
            value = getattr(self, name)
            finite(value, name)
            object.__setattr__(self, name, float(value))
        finite(self.height_min_m + self.height_range_m, "height maximum")
        if self.height_range_m <= 0:
            raise ValueError("height_range_m must be positive")
        if not self.height_min_m <= self.sea_level_m < self.height_min_m + self.height_range_m:
            raise ValueError("sea_level_m must lie in the encoded height interval")
        if type(self.overview_resolution) is not int or not 1 <= self.overview_resolution <= 8192:
            raise ValueError("overview_resolution must be an integer in [1, 8192]")
        if not isinstance(self.parameters, (tuple, list)):
            raise ValueError("parameters must be name/value pairs")
        params = []
        for item in self.parameters:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ValueError("parameters must be name/value pairs")
            name, value = item
            if not isinstance(name, str) or not name:
                raise ValueError("parameter names must be nonempty strings")
            finite(value, name)
            params.append((name, value))
        if len({name for name, _ in params}) != len(params):
            raise ValueError("duplicate parameter name")
        object.__setattr__(self, "parameters", tuple(sorted(params)))

    def to_dict(self) -> dict:
        """Generation-defining state only; paths and coverage are deliberately excluded."""
        return asdict(self)

    @property
    def world_id(self) -> str:
        """Content identity shared by copies of the same reproducible world."""
        return hashlib.sha256(canonical_json(self.to_dict())).hexdigest()

    def flat_position(self, x_m: float, y_m: float) -> tuple[float, float]:
        """Validate a planar sample, canonicalizing only the periodic x axis."""
        if self.geometry != "flat":
            raise ValueError("flat_position requires a flat world")
        finite(x_m, "x_m")
        finite(y_m, "y_m")
        if self.boundary == "wrap_x":
            x_m %= self.width_m
        if not 0 <= x_m < self.width_m or not 0 <= y_m < self.height_m:
            raise ValueError("position lies outside the world")
        return x_m, y_m


@dataclass(frozen=True)
class CoverageRecord:
    """Completed area described by its metadata artifact and content hashes."""

    area_id: str
    artifacts: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        from pathlib import PurePosixPath

        if not isinstance(self.area_id, str) or not self.area_id:
            raise ValueError("area_id must be a nonempty string")
        if not isinstance(self.artifacts, (tuple, list)) or not self.artifacts:
            raise ValueError("coverage must identify its artifacts")
        files = []
        for pair in self.artifacts:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise ValueError("artifact must contain path and SHA-256")
            path, digest = pair
            if (
                not isinstance(path, str)
                or not path
                or "\\" in path
                or PurePosixPath(path).is_absolute()
                or ".." in PurePosixPath(path).parts
                or str(PurePosixPath(path)) != path
                or path == "."
                or path in ("world.json", "coverage.json")
            ):
                raise ValueError("artifact path must be relative and inside the project")
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
            ):
                raise ValueError("artifact requires a lowercase SHA-256 digest")
            files.append((path, digest))
        if len({path for path, _ in files}) != len(files):
            raise ValueError("duplicate artifact path")
        object.__setattr__(self, "artifacts", tuple(sorted(files)))


@dataclass(frozen=True)
class WorldProject:
    definition: WorldDefinition
    coverage: tuple[CoverageRecord, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.definition, WorldDefinition):
            raise ValueError("invalid world definition")
        if not isinstance(self.coverage, (tuple, list)) or any(
            not isinstance(record, CoverageRecord) for record in self.coverage
        ):
            raise ValueError("invalid coverage records")
        if len({record.area_id for record in self.coverage}) != len(self.coverage):
            raise ValueError("duplicate area id")
        paths = [path for record in self.coverage for path, _ in record.artifacts]
        if len(set(paths)) != len(paths):
            raise ValueError("artifact is owned by multiple areas")
        object.__setattr__(self, "coverage", tuple(sorted(self.coverage, key=lambda r: r.area_id)))
