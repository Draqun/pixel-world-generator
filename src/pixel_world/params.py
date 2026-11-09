"""Generation parameters: defaults, validation, serialisation."""

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

    def __post_init__(self) -> None:
        for name in ("seed", "size", "octaves", "erosion_iterations"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer, got {value!r}")
        for name in ("island_exponent", "island_warp"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number, got {value!r}")
        if self.island_exponent <= 0:
            raise ValueError(f"island_exponent must be > 0, got {self.island_exponent}")
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
