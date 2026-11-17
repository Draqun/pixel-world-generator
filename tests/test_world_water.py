import hashlib
import json
from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from pixel_world import world_water as water
from pixel_world.world import WorldDefinition, canonical_json
from pixel_world.writer import create_project


def flat(**kwargs):
    return WorldDefinition(
        seed=42, geometry="flat", geography="region", width_m=16000, height_m=8000, **kwargs
    )


def sphere(**kwargs):
    return WorldDefinition(seed=42, geometry="sphere", geography="world", radius_m=10000, **kwargs)


def enabled(**kwargs):
    return water.HydrologyDefinition(model="hierarchical-v1", backbone_resolution=4, **kwargs)


def test_definition_roundtrip_and_identity():
    settings = enabled()
    saved = json.loads(canonical_json(settings.to_dict()))
    assert water.HydrologyDefinition.from_dict(saved) == settings
    assert saved["refinement_factor"] == 4
    assert saved["limits"]["backbone_cells"] == 1048576
    assert water.HydrologyDefinition().model == "none"
    with pytest.raises(FrozenInstanceError):
        settings.model = "none"
    identity = settings.model_id(flat())
    assert identity == settings.model_id(flat())
    assert identity != replace(settings, min_river_area_m2=2000000).model_id(flat())
    assert identity != settings.model_id(flat(boundary="wrap_x"))
    assert identity != settings.model_id(replace(flat(), seed=43))
    for change in ({"model": "future"}, {"refinement_factor": 2}, {"extra": 1}):
        with pytest.raises(ValueError):
            water.HydrologyDefinition.from_dict(saved | change)
    with pytest.raises(ValueError):
        water.HydrologyDefinition.from_dict({"model": "hierarchical-v1"})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"model": "unknown"},
        {"backbone_resolution": True},
        {"backbone_resolution": 0},
        {"backbone_resolution": 1.5},
        {"max_refinement_depth": 17},
        {"max_refinement_depth": False},
        {"finest_cell_span_m": float("inf")},
        {"finest_cell_span_m": 0},
        {"min_river_area_m2": float("nan")},
        {"min_lake_area_m2": -1},
        {"min_lake_depth_m": True},
        {"max_channel_width_m": 0},
        {"max_channel_width_m": 65},
        {"major_river_area_m2": 1},
        {"major_lake_area_m2": 1},
    ],
)
def test_definition_rejects_invalid_controls(kwargs):
    with pytest.raises(ValueError):
        water.HydrologyDefinition(**kwargs)


def test_pending_enabled_project_is_rejected_before_any_write(tmp_path):
    out = tmp_path / "new-parent" / "world"
    with pytest.raises(ValueError, match="terrain conditioning"):
        create_project(out, flat(), hydrology=enabled())
    assert not out.parent.exists()
    create_project(tmp_path / "disabled", flat())
    before = {p.name: p.read_bytes() for p in (tmp_path / "disabled").iterdir()}
    with pytest.raises(ValueError, match="terrain conditioning"):
        create_project(tmp_path / "disabled", flat(), hydrology=enabled())
    assert {p.name: p.read_bytes() for p in (tmp_path / "disabled").iterdir()} == before


def test_flat_mesh_assigns_one_budget_to_each_quadrilateral_parent():
    mesh = water.backbone_mesh(flat(), enabled())
    assert mesh.positions.shape == (8, 3)
    assert len(set(mesh.cell_ids)) == 8
    assert mesh.cell_corners.shape == (8, 4, 3)
    assert mesh.triangles.shape == (64, 3)
    assert mesh.areas_m2 == pytest.approx(np.full(8, 16000000))
    assert mesh.areas_m2.sum() == pytest.approx(128000000)
    assert mesh.boundary.all()
    assert mesh.layout.depth == 3  # 4000 / 4**3 = 62.5 m.
    assert np.allclose(mesh.cell_corners.mean(axis=1), mesh.positions)
    assert mesh.edge_neighbours.shape == (8, 4)
    for i, neighbours in enumerate(mesh.neighbours):
        assert i not in neighbours
        assert all(i in mesh.neighbours[j] for j in neighbours)


def test_wrapped_cells_join_only_x_and_share_canonical_edge_ports():
    mesh = water.backbone_mesh(flat(boundary="wrap_x"), enabled())
    assert len(mesh.cell_ids) == 8
    assert mesh.boundary.all()
    left = np.flatnonzero(np.all(mesh.positions[:, :2] == (2000, 2000), axis=1))[0]
    right = np.flatnonzero(np.all(mesh.positions[:, :2] == (14000, 2000), axis=1))[0]
    assert right in mesh.neighbours[left]
    assert mesh.edge_vertices[left, 3] == mesh.edge_vertices[right, 1]
    assert (np.ptp(mesh.triangle_points[:, :, 0], axis=1) <= 4000).all()
    assert mesh.areas_m2.sum() == pytest.approx(128000000)
    narrow_mesh = water.backbone_mesh(replace(flat(boundary="wrap_x"), width_m=1), enabled())
    assert (narrow_mesh.areas_m2 > 0).all()
    assert narrow_mesh.areas_m2.sum() == pytest.approx(8000)


def test_spherical_cells_share_edges_corners_and_cover_poles():
    mesh = water.backbone_mesh(sphere(), enabled())
    assert len(mesh.cell_ids) == 96
    assert len(mesh.triangles) == 768
    assert not mesh.boundary.any()
    assert mesh.areas_m2.sum() == pytest.approx(4 * np.pi * 10000**2, rel=1e-12)
    assert np.linalg.norm(mesh.positions, axis=1) == pytest.approx(np.ones(96))
    assert np.count_nonzero(np.isclose(mesh.vertex_positions[:, 2], 1)) == 1
    assert np.count_nonzero(np.isclose(mesh.vertex_positions[:, 2], -1)) == 1
    assert all(len(adjacent) == 4 for adjacent in mesh.neighbours)
    for i, adjacent in enumerate(mesh.edge_neighbours):
        for edge, j in enumerate(adjacent):
            shared = mesh.edge_vertices[i, edge]
            assert shared in mesh.edge_vertices[j]
            assert i in mesh.neighbours[j]
    reached, stack = set(), [0]
    while stack:
        i = stack.pop()
        if i not in reached:
            reached.add(i)
            stack.extend(mesh.neighbours[i])
    assert len(reached) == 96
    from pixel_world.coordinates import FACES, cube_to_lonlat

    for face in FACES:
        for u, v in ((-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0)):
            lon, lat = np.deg2rad(cube_to_lonlat(face, u, v))
            direction = (np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat))
            assert np.min(np.linalg.norm(mesh.vertex_positions - direction, axis=1)) < 1e-14


def test_resource_preflight_precedes_mesh_allocation(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("mesh allocated before preflight")

    monkeypatch.setattr(np, "empty", forbidden)
    with pytest.raises(ValueError, match="backbone.*budget"):
        water.backbone_mesh(flat(), replace(enabled(), backbone_resolution=8192))
    with pytest.raises(ValueError, match="refinement depth"):
        water.backbone_mesh(flat(), replace(enabled(), max_refinement_depth=1))
    with pytest.raises(ValueError, match="vertical"):
        water.backbone_mesh(replace(flat(), sea_level_m=0), enabled())
    with pytest.raises(ValueError, match="disabled"):
        water.backbone_mesh(flat(), water.HydrologyDefinition())


def test_ocean_connectivity_retains_an_inland_below_datum_bowl():
    mesh = water.backbone_mesh(flat(), replace(enabled(), backbone_resolution=8))
    ground = np.full(len(mesh.cell_ids), 10.0)
    ocean = np.flatnonzero(np.all(mesh.positions[:, :2] == (1000, 1000), axis=1))[0]
    bowl = np.flatnonzero(np.all(mesh.positions[:, :2] == (7000, 3000), axis=1))[0]
    ground[ocean], ground[bowl] = 0, 1
    before = ground.copy()
    result = water.solve_backbone(mesh, ground, 2.0, enabled())
    assert np.flatnonzero(result.sea).tolist() == [ocean]
    assert result.lake[bowl]
    assert result.surface_m[bowl] == 10
    assert result.surface_m[ocean] == 2
    assert not result.sea[bowl]
    np.testing.assert_array_equal(ground, before)
    for i, parent in enumerate(result.targets):
        if parent >= 0:
            assert parent in mesh.neighbours[i]
            assert result.rank[parent] < result.rank[i]
            assert result.surface_m[parent] <= result.surface_m[i]
            assert result.accumulation_m2[parent] >= result.accumulation_m2[i]
    roots = result.targets == -1
    assert result.accumulation_m2[roots].sum() == pytest.approx(128000000)


def test_bounded_landlocked_basin_is_not_an_ocean_and_flat_ground_has_no_lake():
    mesh = water.backbone_mesh(flat(), replace(enabled(), backbone_resolution=8))
    ground = np.full(len(mesh.cell_ids), 10.0)
    middle = np.flatnonzero(~mesh.boundary)[0]
    ground[middle] = 0
    result = water.solve_backbone(mesh, ground, 2, enabled())
    assert not result.sea.any()
    assert result.lake[middle]
    assert (result.targets[mesh.boundary] == -1).all()
    flat_result = water.solve_backbone(mesh, np.full(len(mesh.cell_ids), 10), 2, enabled())
    assert not flat_result.lake.any()
    assert not flat_result.terminal.any()


def test_closed_sphere_without_ocean_terminates_at_lowest_cell():
    mesh = water.backbone_mesh(sphere(), enabled())
    ground = np.full(len(mesh.cell_ids), 30.0)
    ground[17] = 10
    result = water.solve_backbone(mesh, ground, 2, enabled())
    assert not result.sea.any()
    assert np.flatnonzero(result.terminal).tolist() == [17]
    assert np.flatnonzero(result.targets == -1).tolist() == [17]
    assert result.accumulation_m2[17] == pytest.approx(4 * np.pi * 10000**2)
    # A tied minimum has one canonical owner, independent of array traversal.
    ground[:] = 30
    tied = water.solve_backbone(mesh, ground, 2, enabled())
    root = np.flatnonzero(tied.terminal)[0]
    assert mesh.cell_ids[root] == min(mesh.cell_ids)


def test_wrapped_world_without_boundary_ocean_selects_largest_low_component():
    settings = replace(enabled(), backbone_resolution=8)
    mesh = water.backbone_mesh(flat(boundary="wrap_x"), settings)
    ground = np.full(len(mesh.cell_ids), 10.0)
    members = []
    for point in ((1000, 3000), (3000, 3000), (9000, 3000)):
        members.append(np.flatnonzero(np.all(mesh.positions[:, :2] == point, axis=1))[0])
    ground[members] = 0
    result = water.solve_backbone(mesh, ground, 2, settings)
    assert set(np.flatnonzero(result.sea)) == set(members[:2])
    assert result.lake[members[2]]
    # A real y boundary ocean takes priority even when an enclosed component is larger.
    boundary = np.flatnonzero(np.all(mesh.positions[:, :2] == (13000, 1000), axis=1))[0]
    ground[boundary] = 0
    boundary_result = water.solve_backbone(mesh, ground, 2, settings)
    assert np.flatnonzero(boundary_result.sea).tolist() == [boundary]


@pytest.mark.parametrize("bad", [np.array([1]), np.array([float("nan")])])
def test_drainage_rejects_invalid_samples(bad):
    mesh = water.backbone_mesh(flat(), enabled())
    with pytest.raises(ValueError, match="ground"):
        water.solve_backbone(mesh, bad, 2, enabled())


def polygon_area(points):
    a = np.asarray(points)
    b = np.roll(a, -1, axis=0)
    return abs(np.sum(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])) / 2


def contains(points, position):
    a = np.asarray(points)[:, :2]
    edge = np.roll(a, -1, axis=0) - a
    delta = np.asarray(position) - a
    cross = edge[:, 0] * delta[:, 1] - edge[:, 1] * delta[:, 0]
    return np.all(cross >= -1e-8) or np.all(cross <= 1e-8)


def test_authoritative_ocean_facets_clip_at_shared_shoreline():
    mesh = water.backbone_mesh(flat(), enabled())
    ground = mesh.positions[:, 0] / 1000
    drainage = water.solve_backbone(mesh, ground, 4, enabled())
    facets = water.ocean_polygons(mesh, drainage, 4)
    assert sum(polygon_area(f.vertices) for f in facets) < 32000000
    assert all(np.asarray(f.vertices)[:, 0].max() <= 4000 for f in facets)
    assert all(f.ocean_id == facets[0].ocean_id for f in facets)
    assert not any(contains(f.vertices, (7000, 3000)) for f in facets)


def test_ocean_facets_preserve_a_coarse_island_and_do_not_fill_inland_bowls():
    mesh = water.backbone_mesh(flat(), replace(enabled(), backbone_resolution=8))
    ground = np.zeros(len(mesh.cell_ids))
    island = np.flatnonzero(np.all(mesh.positions[:, :2] == (7000, 3000), axis=1))[0]
    ground[island] = 10
    drainage = water.solve_backbone(mesh, ground, 2, enabled())
    facets = water.ocean_polygons(mesh, drainage, 2)
    assert not any(contains(f.vertices, (7000, 3000)) for f in facets)
    assert any(contains(f.vertices, (1, 1)) for f in facets)
    ground[:] = 10
    ground[island] = 0
    inland = water.solve_backbone(mesh, ground, 2, enabled())
    assert water.ocean_polygons(mesh, inland, 2) == ()


def test_spherical_and_wrapped_ocean_facets_share_geometry():
    for world in (sphere(), flat(boundary="wrap_x")):
        mesh = water.backbone_mesh(world, enabled())
        drainage = water.solve_backbone(mesh, np.zeros(len(mesh.cell_ids)), 2, enabled())
        facets = water.ocean_polygons(mesh, drainage, 2)
        assert len(facets) == len(mesh.triangles)
        if world.geometry == "sphere":
            assert all(
                np.linalg.norm(f.vertices, axis=1) == pytest.approx(np.ones(len(f.vertices)))
                for f in facets
            )
            assert len({tuple(p) for f in facets for p in f.vertices}) == len(mesh.vertex_positions)
        else:
            assert all(np.ptp(np.asarray(f.vertices)[:, 0]) <= 4000 for f in facets)


def test_generated_backbone_hashes_ignore_other_streams_and_preserve_disabled_outputs(tmp_path):
    from pixel_world.seeds import step_rng

    for world in (flat(), flat(boundary="wrap_x"), sphere()):
        snapshots = []
        for name in ("first", "second"):
            step_rng(world.seed, "world.water.refinement").random(100)
            step_rng(world.seed, "world.water.basins").random(200)
            result = water.generate_backbone(world, enabled())
            path = tmp_path / name
            path.write_bytes(canonical_json(result.to_dict()))
            snapshots.append(hashlib.sha256(path.read_bytes()).hexdigest())
        assert snapshots[0] == snapshots[1]
        assert result.model_id == enabled().model_id(world)
        assert result.to_dict()["exact_global_drainage"] is False
    create_project(tmp_path / "a", flat())
    create_project(tmp_path / "b", flat(), hydrology=water.HydrologyDefinition())
    assert {p.name: p.read_bytes() for p in (tmp_path / "a").iterdir()} == {
        p.name: p.read_bytes() for p in (tmp_path / "b").iterdir()
    }


def test_backbone_features_have_stable_connections_widths_and_estimated_areas():
    settings = replace(enabled(), min_river_area_m2=1, min_lake_area_m2=1)
    result = water.generate_backbone(sphere(), settings)
    features = {f.feature_id: f for f in result.features}
    assert len(features) == len(result.features)
    assert any(f.kind == "river" for f in features.values())
    for feature in features.values():
        for downstream_id in feature.downstream_ids:
            assert downstream_id in features
            downstream = features[downstream_id]
            if feature.kind == downstream.kind == "river":
                assert downstream.width_m >= feature.width_m
                assert downstream.area_m2 >= feature.area_m2
            assert feature.surface_m[-1] >= downstream.surface_m[0]
    changed = water.generate_backbone(replace(sphere(), seed=43), settings)
    assert canonical_json(changed.to_dict()) != canonical_json(result.to_dict())


def test_one_retained_lake_has_one_spill_connection_and_conserves_all_area():
    settings = replace(enabled(), backbone_resolution=8)
    mesh = water.backbone_mesh(flat(), settings)
    ground = np.where(mesh.boundary, 10.0, 0.0)
    result = water.solve_backbone(mesh, ground, 2, settings)
    assert len(result.lake_groups) == 1
    members = set(result.lake_groups[0])
    outlets = [i for i in members if result.targets[i] not in members]
    assert len(outlets) == 1
    assert result.surface_m[outlets[0]] == 10
    for i, parent in enumerate(result.targets):
        if parent >= 0:
            assert result.rank[parent] < result.rank[i]
        incoming = sum(
            result.accumulation_m2[j] for j in range(len(result.targets)) if result.targets[j] == i
        )
        assert result.accumulation_m2[i] == pytest.approx(mesh.areas_m2[i] + incoming)
    assert result.accumulation_m2[result.targets == -1].sum() == pytest.approx(128000000)


def test_ocean_geometry_limit_fails_before_returning_partial_result(monkeypatch):
    mesh = water.backbone_mesh(sphere(), enabled())
    drainage = water.solve_backbone(mesh, np.zeros(len(mesh.cell_ids)), 2, enabled())
    monkeypatch.setitem(water.LIMITS, "geometry_vertices", 2)
    with pytest.raises(ValueError, match="geometry.*budget"):
        water.ocean_polygons(mesh, drainage, 2)


def test_feature_geometry_and_combined_geometry_obey_the_same_budget(monkeypatch):
    settings = replace(enabled(), min_river_area_m2=1)
    mesh = water.backbone_mesh(flat(), settings)
    dry = water.solve_backbone(mesh, np.full(len(mesh.cell_ids), 10.0), 2, settings)
    monkeypatch.setitem(water.LIMITS, "geometry_vertices", 2)
    with pytest.raises(ValueError, match="geometry.*budget"):
        water.backbone_features(mesh, dry, settings)
    monkeypatch.undo()
    result = water.generate_backbone(sphere(), settings)
    ocean_count = sum(len(f.vertices) for f in result.oceans)
    feature_count = sum(len(f.geometry) for f in result.features)
    assert ocean_count and feature_count
    monkeypatch.setitem(water.LIMITS, "geometry_vertices", max(ocean_count, feature_count))
    with pytest.raises(ValueError, match="geometry.*budget"):
        water.generate_backbone(sphere(), settings)


@pytest.mark.parametrize("bad_value", [complex(1, 2), "1", True])
def test_drainage_does_not_coerce_nonreal_height_samples(bad_value):
    mesh = water.backbone_mesh(flat(), enabled())
    with pytest.raises(ValueError, match="ground"):
        water.solve_backbone(mesh, np.full(len(mesh.cell_ids), bad_value), 2, enabled())


def test_each_parent_cell_has_one_outlet_port_and_a_conserved_local_budget():
    settings = replace(enabled(), backbone_resolution=8)
    for world in (flat(), flat(boundary="wrap_x"), sphere()):
        mesh = water.backbone_mesh(world, settings)
        ground = np.linspace(10, 30, len(mesh.cell_ids))
        result = water.solve_backbone(mesh, ground, 2, settings)
        assert result.outlet_ports.shape == (len(mesh.cell_ids),)
        for i, parent in enumerate(result.targets):
            port = result.outlet_ports[i]
            if parent >= 0:
                assert port in mesh.edge_vertices[i]
                assert port in mesh.edge_vertices[parent]
                edge = np.flatnonzero(mesh.edge_vertices[i] == port)[0]
                assert mesh.edge_neighbours[i, edge] == parent
            elif mesh.boundary[i]:
                assert port in mesh.edge_vertices[i]
                edge = np.flatnonzero(mesh.edge_vertices[i] == port)[0]
                assert mesh.edge_neighbours[i, edge] == -1
            else:
                assert result.terminal[i] and port == -1
            incoming = sum(
                result.accumulation_m2[j]
                for j in range(len(mesh.cell_ids))
                if result.targets[j] == i
            )
            assert result.accumulation_m2[i] == pytest.approx(mesh.areas_m2[i] + incoming)


def test_diagonal_low_cells_do_not_create_a_false_ocean_connection():
    settings = replace(enabled(), backbone_resolution=8)
    mesh = water.backbone_mesh(flat(), settings)
    ground = np.full(len(mesh.cell_ids), 10.0)
    # Two diagonal below-datum sites are not four-neighbour connected.
    a = np.flatnonzero(np.all(mesh.positions[:, :2] == (1000, 1000), axis=1))[0]
    b = np.flatnonzero(np.all(mesh.positions[:, :2] == (3000, 3000), axis=1))[0]
    ground[a] = ground[b] = -100
    result = water.solve_backbone(mesh, ground, 2, settings)
    assert np.flatnonzero(result.sea).tolist() == [a]
    facets = water.ocean_polygons(mesh, result, 2)
    assert not any(contains(f.vertices, (3000, 3000)) for f in facets)


def test_river_geometry_uses_its_shared_port_and_reaches_the_true_world_edge():
    settings = replace(enabled(), backbone_resolution=8, min_river_area_m2=1)
    mesh = water.backbone_mesh(flat(), settings)
    ground = np.where(mesh.boundary, 10.0, 30.0)
    drainage = water.solve_backbone(mesh, ground, 2, settings)
    features = water.backbone_features(mesh, drainage, settings)
    assert any(f.kind == "river" for f in features)
    for feature in features:
        if feature.kind == "river":
            source = mesh.cell_ids.index(feature.nodes[0])
            port = drainage.outlet_ports[source]
            assert feature.geometry[1] == tuple(mesh.vertex_positions[port, :2])
            assert len(feature.geometry) == len(feature.surface_m) == 3
            assert all(
                a >= b for a, b in zip(feature.surface_m[:-1], feature.surface_m[1:], strict=True)
            )
        elif feature.kind == "world-outlet":
            x, y = feature.geometry[-1]
            assert x in (0, 16000) or y in (0, 8000)


def test_default_planet_backbone_is_bounded_independently_of_physical_extent():
    settings = water.HydrologyDefinition(model="hierarchical-v1")
    planet = replace(sphere(), radius_m=6371000)
    small = water.backbone_layout(sphere(), settings)
    large = water.backbone_layout(planet, settings)
    assert small.cells == large.cells == 24576
    assert small.vertices == large.vertices == 98306
    result = water.generate_backbone(planet, settings)
    assert len(result.mesh.cell_ids) == 24576
    assert (
        sum(len(f.vertices) for f in result.oceans) + sum(len(f.geometry) for f in result.features)
        <= 1048576
    )
    assert result.drainage.accumulation_m2[result.drainage.targets == -1].sum() == pytest.approx(
        4 * np.pi * 6371000**2
    )
