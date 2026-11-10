"""Version-1 cube-sphere atlas and world-anchored azimuthal equidistant grids."""

import math

from pixel_world.world import finite

# Normal, right, down. Equal dominant axes belong to x before y before z.
FACES = {
    "+x": ((1, 0, 0), (0, 1, 0), (0, 0, -1)),
    "-x": ((-1, 0, 0), (0, -1, 0), (0, 0, -1)),
    "+y": ((0, 1, 0), (-1, 0, 0), (0, 0, -1)),
    "-y": ((0, -1, 0), (1, 0, 0), (0, 0, -1)),
    "+z": ((0, 0, 1), (0, 1, 0), (1, 0, 0)),
    "-z": ((0, 0, -1), (0, 1, 0), (-1, 0, 0)),
}
MAX_SCALE_ERROR = 0.01


def _dot(a: tuple, b: tuple) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _direction(lon: float, lat: float) -> tuple[float, float, float]:
    finite(lon, "longitude")
    finite(lat, "latitude")
    if not -90 <= lat <= 90:
        raise ValueError("latitude must be in [-90, 90]")
    if abs(lat) == 90:
        return 0.0, 0.0, math.copysign(1.0, lat)
    lon, lat = math.radians((lon + 180) % 360 - 180), math.radians(lat)
    return math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)


def _lonlat(point: tuple) -> tuple[float, float]:
    x, y, z = point
    longitude = (math.degrees(math.atan2(y, x)) + 180) % 360 - 180
    if math.hypot(x, y) < 1e-15:
        longitude = 0.0
    return longitude, math.degrees(math.atan2(z, math.hypot(x, y)))


def _cube_direction(face: str, u: float, v: float) -> tuple[float, float, float]:
    if not isinstance(face, str) or face not in FACES:
        raise ValueError("unknown cube face")
    finite(u, "u")
    finite(v, "v")
    if not -1 <= u <= 1 or not -1 <= v <= 1:
        raise ValueError("face coordinates must be in [-1, 1]")
    normal, right, down = FACES[face]
    point = tuple(normal[i] + u * right[i] + v * down[i] for i in range(3))
    length = math.hypot(*point)
    return tuple(value / length for value in point)


def _cube(point: tuple) -> tuple[str, float, float]:
    largest = max(abs(value) for value in point)
    # Roundoff at a mathematical seam must not assign ownership to a different face.
    axis = next(
        i for i in range(3) if math.isclose(abs(point[i]), largest, abs_tol=1e-15, rel_tol=0)
    )
    face = ("+" if point[axis] >= 0 else "-") + "xyz"[axis]
    normal, right, down = FACES[face]
    denominator = _dot(point, normal)
    return (
        face,
        max(-1.0, min(1.0, _dot(point, right) / denominator)),
        max(-1.0, min(1.0, _dot(point, down) / denominator)),
    )


def lonlat_to_cube(lon: float, lat: float) -> tuple[str, float, float]:
    """Degrees to canonical face and dimensionless coordinates in [-1, 1]."""
    return _cube(_direction(lon, lat))


def cube_to_lonlat(face: str, u: float, v: float) -> tuple[float, float]:
    """Face sample to longitude [-180, 180) and latitude [-90, 90] degrees."""
    return _lonlat(_cube_direction(face, u, v))


def canonical_cube(face: str, u: float, v: float) -> tuple[str, float, float]:
    """Give shared edge/corner positions one owner regardless of source face."""
    return _cube(_cube_direction(face, u, v))


def _radius(radius_m: float) -> None:
    finite(radius_m, "radius_m")
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")


def _angle(a: tuple, b: tuple) -> float:
    cross = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    return math.atan2(math.hypot(*cross), _dot(a, b))


def surface_distance(
    lon_a: float, lat_a: float, lon_b: float, lat_b: float, radius_m: float
) -> float:
    """Shortest great-circle distance in metres, including poles and antipodes."""
    _radius(radius_m)
    return radius_m * _angle(_direction(lon_a, lat_a), _direction(lon_b, lat_b))


def projection_scale_error(distance_m: float, radius_m: float) -> float:
    """Maximum tangential scale excess on an equidistant disk of this radius."""
    _radius(radius_m)
    finite(distance_m, "distance_m")
    if distance_m < 0:
        raise ValueError("distance_m must be non-negative")
    angle = distance_m / radius_m
    if angle >= math.pi:
        raise ValueError("projection cannot include the antipode")
    return angle / math.sin(angle) - 1 if angle else 0.0


def _basis(lon: float, lat: float) -> tuple:
    origin = _direction(lon, lat)
    lon, lat = map(math.radians, _lonlat(origin))
    east = (-math.sin(lon), math.cos(lon), 0)
    north = (-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat))
    return origin, east, north


def _check_disk(distance: float, radius: float) -> None:
    if projection_scale_error(distance, radius) > MAX_SCALE_ERROR:
        raise ValueError("local projection distortion exceeds 1%; choose a smaller area")


def local_to_lonlat(
    origin_lon: float, origin_lat: float, x_m: float, y_m: float, radius_m: float
) -> tuple[float, float]:
    """East/right, south/down offsets in a fixed project grid; reject >1% scale error."""
    finite(x_m, "x_m")
    finite(y_m, "y_m")
    origin, east, north = _basis(origin_lon, origin_lat)
    distance = math.hypot(x_m, y_m)
    _check_disk(distance, radius_m)
    if distance == 0:
        return _lonlat(origin)
    angle = distance / radius_m
    return _lonlat(
        tuple(
            math.cos(angle) * origin[i]
            + math.sin(angle) * (x_m / distance * east[i] - y_m / distance * north[i])
            for i in range(3)
        )
    )


def lonlat_to_local(
    origin_lon: float, origin_lat: float, lon: float, lat: float, radius_m: float
) -> tuple[float, float]:
    """Invert the same fixed projection; a tile must not choose a new origin."""
    origin, east, north = _basis(origin_lon, origin_lat)
    point = _direction(lon, lat)
    _radius(radius_m)
    distance = radius_m * _angle(origin, point)
    _check_disk(distance, radius_m)
    x, y = _dot(point, east), -_dot(point, north)
    length = math.hypot(x, y)
    if distance == 0:
        return 0.0, 0.0
    return distance * x / length, distance * y / length
