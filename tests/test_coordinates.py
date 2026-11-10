import math

import pytest

from pixel_world.coordinates import (
    canonical_cube,
    cube_to_lonlat,
    local_to_lonlat,
    lonlat_to_cube,
    lonlat_to_local,
    projection_scale_error,
    surface_distance,
)


@pytest.mark.parametrize(
    "lon,lat,face",
    [
        (0, 0, "+x"),
        (90, 0, "+y"),
        (-90, 0, "-y"),
        (180, 0, "-x"),
        (0, 90, "+z"),
        (0, -90, "-z"),
    ],
)
def test_axes_and_poles(lon, lat, face):
    actual_face, u, v = lonlat_to_cube(lon, lat)
    assert actual_face == face
    assert (u, v) == pytest.approx((0, 0), abs=1e-15)
    assert cube_to_lonlat(face, 0, 0) == pytest.approx(
        (0 if abs(lat) == 90 else (lon + 180) % 360 - 180, lat)
    )


@pytest.mark.parametrize("lon,lat", [(179.9, 30), (-179.9, -30), (45, 35), (32, 89.9), (-70, -83)])
def test_round_trips(lon, lat):
    assert cube_to_lonlat(*lonlat_to_cube(lon, lat)) == pytest.approx((lon, lat), abs=1e-10)


def test_canonical_seams_corners_and_longitude():
    assert canonical_cube("+x", 1, 0) == canonical_cube("+y", -1, 0) == ("+x", 1, 0)
    assert canonical_cube("+x", 1, -1) == canonical_cube("+z", 1, 1) == ("+x", 1, -1)
    assert lonlat_to_cube(-180, 25) == lonlat_to_cube(180, 25)
    assert lonlat_to_cube(12, 90) == lonlat_to_cube(175, 90)


def test_great_circle_distances():
    assert surface_distance(0, 0, 90, 0, 100) == pytest.approx(50 * math.pi)
    assert surface_distance(0, 90, 180, -90, 100) == pytest.approx(100 * math.pi)
    assert surface_distance(180, 30, -180, 30, 100) == pytest.approx(0, abs=1e-10)
    assert surface_distance(0, 90, 90, 90, 100) == 0


@pytest.mark.parametrize("origin", [(0, 0), (179.99, 45), (0, 90), (-45, -90)])
def test_anchored_local_grid_roundtrip_and_radial_distance(origin):
    lon, lat = local_to_lonlat(*origin, 1000, 2000, 6000000)
    assert lonlat_to_local(*origin, lon, lat, 6000000) == pytest.approx((1000, 2000), abs=1e-6)
    assert surface_distance(*origin, lon, lat, 6000000) == pytest.approx(
        math.hypot(1000, 2000), abs=1e-6
    )
    assert local_to_lonlat(*origin, 0, 0, 6000000) == (
        0 if abs(origin[1]) == 90 else origin[0],
        origin[1],
    )


def test_projection_distortion_is_bounded_and_rejects_large_areas():
    assert projection_scale_error(0, 100) == 0
    assert projection_scale_error(10, 100) == pytest.approx(0.00166861316)
    with pytest.raises(ValueError, match="distortion"):
        local_to_lonlat(0, 0, 100, 0, 100)
    with pytest.raises(ValueError, match="distortion"):
        lonlat_to_local(0, 0, 90, 0, 100)


@pytest.mark.parametrize(
    "call",
    [
        lambda: lonlat_to_cube(0, 91),
        lambda: lonlat_to_cube(math.inf, 0),
        lambda: cube_to_lonlat("bad", 0, 0),
        lambda: cube_to_lonlat("+x", 2, 0),
        lambda: surface_distance(0, 0, 1, 1, -1),
        lambda: projection_scale_error(-1, 10),
        lambda: local_to_lonlat(0, 0, math.nan, 0, 100),
    ],
)
def test_invalid_coordinates(call):
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize("face", ["+x", "-x", "+y", "-y", "+z", "-z"])
@pytest.mark.parametrize(
    "u,v", [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1), (0.3, -0.7)]
)
def test_every_face_edge_corner_and_interior_roundtrips(face, u, v):
    canonical = canonical_cube(face, u, v)
    lon, lat = cube_to_lonlat(face, u, v)
    actual = lonlat_to_cube(lon, lat)
    assert actual[0] == canonical[0]
    assert actual[1:] == pytest.approx(canonical[1:], abs=1e-14)
    assert cube_to_lonlat(*canonical) == pytest.approx((lon, lat), abs=1e-12)
