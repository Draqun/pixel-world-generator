"""Generation parameters: defaults, validation, serialisation."""

import math
from dataclasses import asdict, dataclass

SIZE_MIN = 64
SIZE_MAX = 8192


@dataclass(frozen=True)
class Params:
    seed: int
    size: int = 1024
    octaves: int = 6
    erosion_iterations: int = 50
    island_exponent: float = 2.5
    island_warp: float = 0.25
    erosion_strength: float = 0.04
    erosion_talus: float = 0.004
    height_range_m: float = 400.0
    sea_level: float = 0.2
    min_lake_depth_m: float = 1.0

    def __post_init__(self) -> None:
        for name in ("seed", "size", "octaves", "erosion_iterations"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer, got {value!r}")
        for name in (
            "island_exponent",
            "island_warp",
            "erosion_strength",
            "erosion_talus",
            "height_range_m",
            "sea_level",
            "min_lake_depth_m",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number, got {value!r}")
        if not math.isfinite(self.sea_level) or not 0 <= self.sea_level < 1:
            raise ValueError("sea_level must be finite and in [0, 1)")
        if not math.isfinite(self.min_lake_depth_m) or self.min_lake_depth_m < 0:
            raise ValueError("min_lake_depth_m must be finite and >= 0")
        if not math.isfinite(self.height_range_m):
            raise ValueError("height_range_m must be finite")
        if self.island_exponent <= 0:
            raise ValueError(f"island_exponent must be > 0, got {self.island_exponent}")
        if self.erosion_strength < 0:
            raise ValueError(f"erosion_strength must be >= 0, got {self.erosion_strength}")
        if self.height_range_m <= 0:
            raise ValueError(f"height_range_m must be > 0, got {self.height_range_m}")
        if self.erosion_talus <= 0:
            raise ValueError(f"erosion_talus must be > 0, got {self.erosion_talus}")
        if self.island_warp < 0:
            raise ValueError(f"island_warp must be >= 0, got {self.island_warp}")
        if self.seed < 0:
            raise ValueError(f"seed must be >= 0, got {self.seed}")
        if not SIZE_MIN <= self.size <= SIZE_MAX:
            raise ValueError(f"size must be between {SIZE_MIN} and {SIZE_MAX}, got {self.size}")
        if self.octaves < 1:
            raise ValueError(f"octaves must be >= 1, got {self.octaves}")
        if self.erosion_iterations < 0:
            raise ValueError(f"erosion_iterations must be >= 0, got {self.erosion_iterations}")

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)
