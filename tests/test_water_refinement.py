import hashlib
from dataclasses import replace

import numpy as np
import pytest

from pixel_world import water_refinement as fine
from pixel_world import world_water as water
from pixel_world.seeds import step_rng
from pixel_world.world import WorldDefinition, canonical_json


def world(geometry="flat", **kwargs):
    dimensions = (
        {"radius_m": 2000} if geometry == "sphere" else {"width_m": 16000, "height_m": 16000}
    )
    return WorldDefinition(seed=42, geometry=geometry, geography="world", **(dimensions | kwargs))


def settings(**kwargs):
    return water.HydrologyDefinition(model="hierarchical-v1", backbone_resolution=4, **kwargs)


def backbone(definition=None, **kwargs):
    return water.generate_backbone(definition or world(), settings(**kwargs))


def test_root_context_uses_the_same_port_from_both_sides_of_a_spherical_seam():
    base = backbone(world("sphere"))
    contexts = fine.root_cells(base)
    assert len(contexts) == 96
    for i, context in enumerate(contexts):
        assert context.local_area_m2 == base.mesh.areas_m2[i]
        assert context.total_area_m2 == pytest.approx(base.drainage.accumulation_m2[i])
        for incoming in context.incoming:
            upstream = [
                c
                for c in contexts
                if c.outlet.port_id == incoming.port_id and c.address != context.address
            ]
            assert len(upstream) == 1
            assert upstream[0].outlet == incoming
            assert upstream[0].address.face != context.address.face or (
                abs(upstream[0].address.x - context.address.x)
                + abs(upstream[0].address.y - context.address.y)
                == 1
            )


def test_patch_injects_imported_flux_once_and_conserves_local_source_area():
    base = backbone()
    parent = fine.root_cells(base)[5]
    a = fine.flow_port(base, parent.address, 1.0, 0.0, 20.0, 300.0)
    b = fine.flow_port(base, parent.address, 0.0, 1.0, 20.0, 700.0)
    outlet = fine.flow_port(base, parent.address, 1.0, 0.5, 10.0, 16001000.0)
    parent = replace(
        parent,
        incoming=(a, b),
        outlet=outlet,
        surface_m=15.0,
        inherited=(),
        footprints=(),
        anchor=None,
    )
    patch = fine.refine_patch(base, parent, np.full(16, 30.0))
    assert patch.local_areas_m2.sum() == pytest.approx(16000000)
    assert patch.injected_m2.sum() == 1000
    assert np.count_nonzero(patch.injected_m2) == 2
    sink = np.flatnonzero(patch.targets == -1)
    assert len(sink) == 1
    assert patch.accumulation_m2[sink[0]] == pytest.approx(16001000)
    assert patch.children[sink[0]].outlet == outlet
    for i, target in enumerate(patch.targets):
        if target >= 0:
            assert patch.rank[target] < patch.rank[i]
            assert patch.surfaces_m[target] <= patch.surfaces_m[i]
        child = patch.children[i]
        assert child.total_area_m2 == pytest.approx(patch.accumulation_m2[i])
        assert child.local_area_m2 == patch.local_areas_m2[i]
    assert [c.address.level for c in patch.children] == [1] * 16
    assert len({c.address for c in patch.children}) == 16


def test_refinement_does_not_change_parent_geometry_or_depend_on_query_order():
    base = backbone()
    parents = fine.root_cells(base)
    before = canonical_json(base.to_dict())
    first = {p.address: canonical_json(fine.refine_cell(base, p).to_dict()) for p in parents[:4]}
    second = {
        p.address: canonical_json(fine.refine_cell(base, p).to_dict())
        for p in reversed(parents[:4])
    }
    assert first == second
    assert canonical_json(base.to_dict()) == before


def test_children_reach_saved_finest_scale_without_evaluating_upstream_patches():
    base = backbone()
    parent = fine.root_cells(base)[5]
    count = 0
    while parent.address.level < base.mesh.layout.depth:
        patch = fine.refine_cell(base, parent)
        parent = patch.children[0]
        count += 1
    assert count == 3
    with pytest.raises(ValueError, match="finest"):
        fine.refine_cell(base, parent)


def test_local_tributaries_join_an_unchanged_parent_and_keep_monotone_widths():
    base = backbone(min_river_area_m2=1, min_lake_area_m2=1000000000, major_lake_area_m2=1000000000)
    parent = next(p for p in fine.root_cells(base) if p.anchor is not None)
    before = canonical_json(parent.anchor.__dict__)
    patch = fine.refine_patch(base, parent, np.full(16, parent.surface_m + 20))
    tributaries = [f for f in patch.features if f.kind == "river"]
    assert len(tributaries) > 1
    receivers = {f.feature_id: f for f in (*parent.inherited, *patch.features)}
    for feature in tributaries:
        assert feature.parent_id == parent.address.key
        recipient = receivers[feature.downstream_ids[0]]
        assert feature.width_m <= recipient.width_m
        assert feature.area_m2 <= recipient.area_m2
        end = np.asarray(feature.geometry[-1])
        distances = []
        for a, b in zip(recipient.geometry[:-1], recipient.geometry[1:], strict=True):
            a, b = np.asarray(a), np.asarray(b)
            vector = b - a
            t = (
                np.clip(np.dot(end - a, vector) / np.dot(vector, vector), 0, 1)
                if np.dot(vector, vector)
                else 0
            )
            distances.append(np.linalg.norm(end - (a + t * vector)))
        assert min(distances) < 1e-8
        assert feature.surface_m[0] >= feature.surface_m[-1]
    assert canonical_json(parent.anchor.__dict__) == before


def test_retained_small_lake_is_owned_once_by_its_parent_patch():
    base = backbone(min_river_area_m2=1)
    parent = next(p for p in fine.root_cells(base) if p.anchor is not None)
    parent = replace(parent, footprints=())
    ground = np.full(16, parent.surface_m + 20)
    ground[0] = parent.surface_m - 10
    patch = fine.refine_patch(base, parent, ground)
    lakes = [f for f in patch.features if f.kind == "lake"]
    assert lakes
    facets = [p for p in patch.footprints if p.kind == "lake"]
    assert facets
    assert {p.feature_id for p in facets} == {f.feature_id for f in lakes}
    for lake in lakes:
        assert lake.parent_id == parent.address.key
        assert len(set(lake.surface_m)) == 1
        assert lake.downstream_ids
        assert lake.area_m2 >= base.settings.min_lake_area_m2


def test_inherited_large_lake_geometry_is_shared_across_parent_cells():
    base = backbone()
    mesh = base.mesh
    ground = np.where(mesh.boundary, 100.0, 10.0)
    drainage = water.solve_backbone(mesh, ground, 2.0, base.settings)
    features = water.backbone_features(mesh, drainage, base.settings)
    base = replace(base, drainage=drainage, features=features, oceans=())
    parents = fine.root_cells(base)
    wet = [p for p in parents if any(f.kind == "lake" for f in p.footprints)]
    assert len(wet) > 1
    identities = {f.feature_id for p in wet for f in p.footprints}
    assert len(identities) == 1
    surfaces = {f.surface_m for p in wet for f in p.footprints}
    assert surfaces == {100.0}
    for parent in wet:
        before = canonical_json([p.__dict__ for p in parent.footprints])
        patch = fine.refine_cell(base, parent)
        inherited = [
            p for child in patch.children for p in child.footprints if p.feature_id in identities
        ]
        assert inherited
        assert all(p.surface_m == 100.0 for p in inherited)
        assert canonical_json([p.__dict__ for p in parent.footprints]) == before
        for i, target in enumerate(patch.targets):
            if target >= 0:
                assert patch.surfaces_m[i] >= patch.surfaces_m[target]
                assert patch.children[i].outlet.surface_m <= patch.surfaces_m[i]


@pytest.mark.parametrize("definition", [world(), world("sphere"), replace(world(), seed=43)])
def test_parent_anchor_is_its_own_channel_not_an_upstream_neighbours_segment(definition):
    base = backbone(definition, min_river_area_m2=1)
    for i, parent in enumerate(fine.root_cells(base)):
        if parent.anchor is not None:
            assert parent.anchor.nodes[0] == base.mesh.cell_ids[i]
            if base.world.geometry == "sphere":
                continue
            patch = fine.refine_cell(base, parent)
            x0, y0, x1, y1 = parent.address.bounds
            x0, x1 = x0 * 4000, x1 * 4000
            y0, y1 = y0 * 4000, y1 * 4000
            for feature in patch.features:
                assert all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in feature.geometry)


def feature_bytes(result):
    return {feature.feature_id: canonical_json(feature.__dict__) for feature in result.features}


def test_crop_overlap_split_and_repeat_queries_share_identical_feature_geometry(tmp_path):
    base = backbone(min_river_area_m2=1)
    whole = fine.WaterWindow("flat", 1.0, 1.0, 1.1, 1.1)
    left = fine.WaterWindow("flat", 1.0, 1.0, 1.05, 1.1)
    right = fine.WaterWindow("flat", 1.05, 1.0, 1.1, 1.1)
    full = fine.query_water(base, (whole,))
    a = fine.query_water(base, (left,))
    b = fine.query_water(base, (right,))
    union = fine.query_water(base, (right, left, left))
    assert feature_bytes(union) == feature_bytes(full)
    shared = feature_bytes(a).keys() & feature_bytes(b).keys()
    assert shared
    assert all(feature_bytes(a)[key] == feature_bytes(b)[key] for key in shared)
    hashes = []
    for name in ("first", "second"):
        step_rng(base.world.seed, "world.water.basins").random(100)
        result = fine.query_water(base, (whole,))
        path = tmp_path / name
        path.write_bytes(canonical_json(result.to_dict()))
        hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
    assert hashes[0] == hashes[1]
    assert full.cache_bytes == 0
    assert full.max_live_patches <= base.mesh.layout.depth


def test_query_crosses_wrapped_and_cube_boundaries_without_changing_ports():
    base = backbone(world(boundary="wrap_x"), min_river_area_m2=1)
    cross = fine.query_water(base, (fine.WaterWindow("flat", 3.9, 1.0, 4.1, 1.1),))
    parts = fine.query_water(
        base,
        (
            fine.WaterWindow("flat", 3.9, 1.0, 4.0, 1.1),
            fine.WaterWindow("flat", 0.0, 1.0, 0.1, 1.1),
        ),
    )
    assert feature_bytes(cross) == feature_bytes(parts)
    sphere = backbone(world("sphere"), min_river_area_m2=1)
    for face in ("+x", "+y", "+z"):
        result = fine.query_water(sphere, (fine.WaterWindow(face, 0.0, 0.0, 0.01, 0.01),))
        assert result.patches_evaluated > 0
        assert result.max_live_patches <= sphere.mesh.layout.depth


def test_query_work_limits_fail_before_refinement_and_do_not_expand_upstream(monkeypatch):
    base = backbone()

    def forbidden(*args, **kwargs):
        pytest.fail("patch evaluated before work preflight")

    monkeypatch.setattr(fine, "refine_cell", forbidden)
    monkeypatch.setitem(water.LIMITS, "refinement_patches", 1)
    with pytest.raises(ValueError, match="patch.*budget"):
        fine.query_water(base, (fine.WaterWindow("flat", 0.0, 0.0, 4.0, 4.0),))
    monkeypatch.undo()
    for definition in (world(), world(width_m=16000000, height_m=16000000)):
        base = backbone(definition)
        scale = 4 / definition.width_m
        query = fine.WaterWindow("flat", 8000 * scale, 8000 * scale, 8512 * scale, 8512 * scale)
        result = fine.query_water(base, (query,))
        assert result.patches_evaluated <= 16 * base.mesh.layout.depth
        assert result.cache_bytes == 0
        assert result.max_live_patches <= base.mesh.layout.depth


@pytest.mark.parametrize(
    "window",
    [
        ("flat", 0.0, 0.0, 0.0, 1.0),
        ("bad", 0.0, 0.0, 1.0, 1.0),
        ("flat", float("nan"), 0.0, 1.0, 1.0),
    ],
)
def test_invalid_window_is_rejected(window):
    with pytest.raises(ValueError):
        fine.WaterWindow(*window)


def test_new_tributary_does_not_cross_an_unrelated_inherited_channel():
    base = backbone(min_river_area_m2=1, min_lake_area_m2=1e9, major_lake_area_m2=1e9)
    parent = next(p for p in fine.root_cells(base) if p.anchor is not None)
    x0, y0, x1, y1 = parent.address.bounds
    barrier = water.WaterFeature(
        "barrier",
        "river",
        ("a", "b"),
        ((x0 * 4000, (y0 + 0.35) * 4000), (x1 * 4000, (y0 + 0.35) * 4000)),
        (parent.anchor.feature_id,),
        (parent.surface_m, parent.surface_m),
        1.0,
        1.0,
    )
    parent = replace(parent, inherited=(barrier, parent.anchor), footprints=())
    patch = fine.refine_patch(base, parent, np.full(16, parent.surface_m + 20))
    assert not any(
        f.kind == "river" and f.geometry[0][1] < (y0 + 0.35) * 4000 for f in patch.features
    )


def test_invalid_depth_model_and_geometry_fail_before_sampling(monkeypatch):
    base = backbone()
    parent = fine.root_cells(base)[0]

    def forbidden(*args, **kwargs):
        pytest.fail("terrain sampled before validation")

    monkeypatch.setattr(fine, "_children_geometry", forbidden)
    for invalid in (
        replace(parent, address=fine.CellAddress("flat", base.mesh.layout.depth, 0, 0)),
        replace(parent, model_id="other-model"),
        replace(parent, address=fine.CellAddress("+x", 0, 0, 0)),
    ):
        with pytest.raises(ValueError):
            fine.refine_cell(base, invalid)


def test_refinement_geometry_limit_and_depth_rejection():
    base = backbone(min_river_area_m2=1, min_lake_area_m2=1e9, major_lake_area_m2=1e9)
    parent = next(p for p in fine.root_cells(base) if p.anchor is not None)
    with pytest.MonkeyPatch.context() as m:
        m.setitem(water.LIMITS, "geometry_vertices", 1)
        # The parent retains its model identity under this injected limit for this check.
        parent = replace(parent, model_id=base.model_id)
        with pytest.raises(ValueError, match="geometry.*budget"):
            fine.refine_patch(base, parent, np.full(16, parent.surface_m + 20))


@pytest.mark.parametrize("definition", [world(), world(boundary="wrap_x"), world("sphere")])
def test_a_coarse_port_and_its_child_corner_have_identical_identity(definition):
    base = backbone(definition)
    for parent in fine.root_cells(base)[:8]:
        a = parent.address
        coarse = fine.flow_port(base, a, 1.0, 0.5, 20.0, 200.0)
        child = fine.CellAddress(a.face, 1, a.x * 4 + 3, a.y * 4 + 2)
        corner = fine.flow_port(base, child, 1.0, 0.0, 20.0, 200.0)
        assert coarse == corner


def test_small_lake_crossing_a_query_boundary_keeps_one_identity_and_surface():
    base = backbone(min_river_area_m2=1)
    selected = None
    for parent in fine.root_cells(base):
        patch = fine.refine_cell(base, parent)
        if patch.footprints:
            selected = patch.footprints[0]
            break
    assert selected is not None
    coordinates = np.asarray(selected.vertices)[:, :2] / 4000
    x0, y0 = coordinates.min(axis=0)
    x1, y1 = coordinates.max(axis=0)
    middle = (x0 + x1) / 2
    left = fine.query_water(
        base, (fine.WaterWindow("flat", float(x0), float(y0), float(middle), float(y1)),)
    )
    right = fine.query_water(
        base, (fine.WaterWindow("flat", float(middle), float(y0), float(x1), float(y1)),)
    )
    a = [p for p in left.footprints if p.feature_id == selected.feature_id]
    b = [p for p in right.footprints if p.feature_id == selected.feature_id]
    assert a and a == b
    assert all(p.surface_m == selected.surface_m for p in a)


def test_terminal_basin_refinement_retains_the_prescribed_sink_connection():
    base = backbone(world("sphere"), min_river_area_m2=1)
    mesh = base.mesh
    ground = np.full(len(mesh.cell_ids), 100.0)
    ground[0] = 20.0
    drainage = water.solve_backbone(mesh, ground, 2.0, base.settings)
    features = water.backbone_features(mesh, drainage, base.settings)
    base = replace(base, drainage=drainage, features=features, oceans=())
    parent = fine.root_cells(base)[0]
    patch = fine.refine_patch(base, parent, np.full(16, 100.0))
    sink = np.flatnonzero(patch.targets == -1)[0]
    assert patch.children[sink].outlet == parent.outlet
    assert parent.destination_id.startswith("terminal-basin:")
    assert patch.accumulation_m2[sink] == pytest.approx(4 * np.pi * 2000**2)


def test_new_lake_does_not_overlap_the_width_of_a_nearby_inherited_river():
    base = backbone(min_river_area_m2=1)
    parent = next(p for p in fine.root_cells(base) if p.anchor is not None)
    x0, y0, x1, y1 = parent.address.bounds
    river = water.WaterFeature(
        "wide-bank",
        "river",
        ("a", "b"),
        ((x0 * 4000, y0 * 4000 + 990), (x1 * 4000, y0 * 4000 + 990)),
        (parent.anchor.feature_id,),
        (parent.surface_m, parent.surface_m),
        1e9,
        64.0,
    )
    parent = replace(parent, inherited=(river,), footprints=())
    ground = np.full(16, parent.surface_m + 20)
    ground[5] = parent.surface_m - 10
    patch = fine.refine_patch(base, parent, ground)
    assert not any(f.kind == "lake" for f in patch.features)


def test_materialized_local_channel_passes_through_its_prescribed_outlet():
    base = backbone(min_river_area_m2=1, min_lake_area_m2=1e9, major_lake_area_m2=1e9)
    parent = next(p for p in fine.root_cells(base) if p.anchor is not None)
    patch = fine.refine_patch(base, parent, np.full(16, parent.surface_m + 20))
    for feature in patch.features:
        if feature.kind != "river":
            continue
        source = next(c for c in patch.children if feature.feature_id == "river:" + c.address.key)
        assert fine._world_position(base, source.outlet.position) in feature.geometry


def test_qualifying_lake_outflow_has_a_connected_spill_channel():
    base = backbone(min_river_area_m2=1)
    parent = next(p for p in fine.root_cells(base) if p.anchor is not None)
    parent = replace(parent, footprints=())
    ground = np.full(16, parent.surface_m + 20)
    ground[0] = parent.surface_m - 10
    patch = fine.refine_patch(base, parent, ground)
    by_id = {f.feature_id: f for f in patch.features}
    lake = next(f for f in patch.features if f.kind == "lake")
    assert lake.downstream_ids[0] in by_id
    spill = by_id[lake.downstream_ids[0]]
    assert spill.kind == "river"
    assert len(lake.outlet_geometry) >= 2
    assert spill.geometry == lake.outlet_geometry
    assert spill.surface_m[0] == lake.surface_m[0]
    assert spill.area_m2 >= base.settings.min_river_area_m2


@pytest.mark.parametrize(
    "definition,address,ground",
    [
        (
            world(boundary="wrap_x"),
            ("flat", 0, 0, 2),
            [41, 182, 27, 157, 124, 115, 58, 77, 95, 129, 98, 28, 36, 162, 0, 96],
        ),
        (
            world("sphere"),
            ("+z", 0, 2, 1),
            [85, 30, 119, 52, 60, 144, 96, 69, 140, 164, 93, 82, 56, 139, 158, 111],
        ),
        (
            world("sphere"),
            ("+y", 0, 3, 3),
            [17, 15, 20, 19, 141, 96, 170, 196, 165, 177, 19, 64, 105, 65, 180, 139],
        ),
    ],
)
def test_fixed_carriers_and_latent_lake_inlets_keep_descending_profiles(
    definition, address, ground
):
    base = backbone(definition)
    parent = next(p for p in fine.root_cells(base) if p.address == fine.CellAddress(*address))
    patch = fine.refine_patch(base, parent, np.asarray(ground, dtype=float))
    for i, target in enumerate(patch.targets):
        assert patch.children[i].outlet.surface_m <= patch.surfaces_m[i] + 1e-9
        if target >= 0:
            assert patch.surfaces_m[i] + 1e-9 >= patch.surfaces_m[target]
    assert patch.accumulation_m2[patch.targets == -1].sum() == pytest.approx(parent.total_area_m2)


def test_inherited_large_lake_has_a_physical_outlet_without_changing_its_record():
    base = backbone(min_river_area_m2=1)
    mesh = base.mesh
    ground = np.where(mesh.boundary, 100.0, 10.0)
    drainage = water.solve_backbone(mesh, ground, 2.0, base.settings)
    features = water.backbone_features(mesh, drainage, base.settings)
    base = replace(base, drainage=drainage, features=features, oceans=())
    before = canonical_json(base.to_dict())
    roots = fine.root_cells(base)
    records = {f.feature_id: f for p in roots for f in p.inherited}
    lake = next(f for f in records.values() if f.kind == "lake")
    assert lake.outlet_feature_id in records
    spill = records[lake.outlet_feature_id]
    assert spill.kind == "river"
    assert spill.geometry == lake.outlet_geometry
    assert spill.surface_m[0] == lake.surface_m[0]
    assert canonical_json(base.to_dict()) == before


def test_new_lake_shores_do_not_relabel_a_different_canonical_port_profile():
    base = backbone(min_river_area_m2=1)
    parent = next(p for p in fine.root_cells(base) if p.anchor is not None)
    parent = replace(parent, footprints=())
    ground = np.full(16, parent.surface_m + 20)
    ground[0] = parent.surface_m - 10
    patch = fine.refine_patch(base, parent, ground)
    assert patch.footprints
    for shape in patch.footprints:
        a = np.asarray(shape.vertices)[:, :2]
        for child in patch.children:
            point = np.asarray(child.outlet.position[:2])
            inside = np.all(point >= a.min(axis=0)) and np.all(point <= a.max(axis=0))
            if inside:
                assert child.outlet.surface_m == shape.surface_m


def test_a_protected_world_outlet_keeps_its_locked_edge_after_lake_selection():
    base = backbone()
    parent = next(
        p for p in fine.root_cells(base) if p.address == fine.CellAddress("flat", 0, 3, 2)
    )
    patch = fine.refine_patch(
        base,
        parent,
        np.asarray([134, 125, 88, 139, 179, 105, 122, 37, 136, 22, 142, 198, 87, 103, 58, 150.0]),
    )
    for child in patch.children:
        for port in child.incoming:
            fine._owner(base, child, port)


def test_planetary_default_backbone_query_keeps_fine_work_local():
    definition = world("sphere", radius_m=6371000)
    base = water.generate_backbone(definition, water.HydrologyDefinition(model="hierarchical-v1"))
    span = 512 * base.mesh.layout.columns / (2 * definition.radius_m)
    result = fine.query_water(
        base, (fine.WaterWindow("+x", 32.125, 32.125, 32.125 + span, 32.125 + span),)
    )
    assert result.patches_evaluated <= 256 * base.mesh.layout.depth
    assert result.max_live_patches <= base.mesh.layout.depth
    assert result.cache_bytes == 0


def test_window_limit_rejects_before_any_root_or_fine_expansion(monkeypatch):
    base = backbone()

    def forbidden(*args, **kwargs):
        pytest.fail("water expanded before window preflight")

    monkeypatch.setattr(fine, "root_cells", forbidden)
    with pytest.raises(ValueError, match="window"):
        fine.query_water(base, (fine.WaterWindow("flat", 0.0, 0.0, 0.01, 0.01),) * 65)


def test_new_spill_cannot_divert_transport_into_a_lower_incidental_sea():
    base = backbone(min_river_area_m2=1)
    parent = next(
        p for p in fine.root_cells(base) if p.address == fine.CellAddress("flat", 0, 2, 3)
    )
    patch = fine.refine_patch(
        base,
        parent,
        np.asarray([90, 121, 166, 44, 168, 194, 122, 129, 110, 69, 120, 81, 100, 28, 14, 86]),
    )
    for feature in patch.features:
        if feature.kind != "river":
            continue
        point = feature.geometry[-1]
        x0, y0, x1, y1 = parent.address.bounds
        endpoint = fine.flow_port(
            base,
            parent.address,
            (point[0] / 4000 - x0) / (x1 - x0),
            (point[1] / 4000 - y0) / (y1 - y0),
            feature.surface_m[-1],
            feature.area_m2,
        )
        child = patch.children[fine._owner(base, parent, endpoint)]
        assert feature.surface_m[-1] + 1e-9 >= child.outlet.surface_m
    for child in patch.children:
        fine.refine_cell(base, child)


def test_wrapped_edge_children_keep_equal_physical_source_areas():
    base = backbone(world(boundary="wrap_x"))
    parent = next(
        p for p in fine.root_cells(base) if p.address == fine.CellAddress("flat", 0, 3, 2)
    )
    patch = fine.refine_cell(base, parent)
    assert patch.local_areas_m2 == pytest.approx(np.full(16, parent.local_area_m2 / 16))


def test_tributary_interface_uses_the_inherited_carrier_surface():
    base = backbone(min_river_area_m2=1)
    parent = next(
        p for p in fine.root_cells(base) if p.address == fine.CellAddress("flat", 0, 1, 2)
    )
    patch = fine.refine_patch(
        base,
        parent,
        np.asarray([71, 93, 112, 192, 84, 92, 194, 42, 107, 7, 11, 18, 117, 100, 108, 194]),
    )
    north, south = patch.children[4], patch.children[8]
    assert patch.targets[4] == 8
    assert north.outlet in south.incoming
    assert north.outlet.surface_m == pytest.approx(107.0432754388)
    child = fine.refine_patch(
        base,
        south,
        np.asarray([173, 93, 127, 153, 175, 17, 80, 97, 164, 135, 176, 142, 173, 30, 113, 128]),
    )
    for i, target in enumerate(child.targets):
        if target >= 0:
            assert child.surfaces_m[i] + 1e-9 >= child.surfaces_m[target]


def test_locked_corner_profile_takes_precedence_over_a_different_edge_midpoint():
    base = backbone(min_river_area_m2=1)
    parent = next(
        p for p in fine.root_cells(base) if p.address == fine.CellAddress("flat", 0, 0, 1)
    )
    patch = fine.refine_patch(
        base,
        parent,
        np.asarray([165, 162, 6, 5, 25, 171, 193, 166, 19, 42, 22, 64, 173, 146, 171, 104]),
    )
    parent = next(c for c in patch.children if c.address == fine.CellAddress("flat", 1, 2, 6))
    child = fine.refine_patch(
        base,
        parent,
        np.asarray([3, 104, 60, 4, 140, 8, 103, 23, 107, 168, 137, 111, 159, 151, 50, 124]),
    )
    assert child.targets[10] == 9
    assert child.children[10].outlet.surface_m == pytest.approx(151.3280702970)
    assert child.children[10].outlet in child.children[9].incoming


@pytest.mark.parametrize(
    "boundary,root_address,root_ground,child_address,child_ground",
    [
        (
            "bounded",
            (1, 3),
            [36, 60, 146, 122, 50, 66, 108, 90, 130, 193, 11, 130, 185, 179, 7, 113],
            (6, 13),
            [186, 106, 50, 105, 18, 180, 101, 104, 113, 18, 176, 76, 150, 85, 107, 90],
        ),
        (
            "bounded",
            (3, 1),
            [151, 95, 141, 147, 91, 73, 194, 21, 75, 114, 185, 40, 134, 160, 163, 125],
            (14, 6),
            [171, 187, 57, 110, 96, 68, 92, 128, 8, 57, 29, 26, 64, 181, 120, 43],
        ),
        (
            "wrap_x",
            (3, 1),
            [170, 79, 131, 158, 198, 178, 40, 78, 157, 122, 97, 159, 56, 138, 10, 106],
            (14, 6),
            [144, 100, 23, 81, 154, 126, 140, 122, 124, 187, 191, 125, 44, 180, 137, 191],
        ),
    ],
)
def test_new_carriers_preserve_low_inlets_and_corner_outlet_access(
    boundary, root_address, root_ground, child_address, child_ground
):
    base = backbone(world(boundary=boundary), min_river_area_m2=1)
    parent = next(
        p for p in fine.root_cells(base) if p.address == fine.CellAddress("flat", 0, *root_address)
    )
    patch = fine.refine_patch(base, parent, np.asarray(root_ground))
    ports = {p.port_id: p for c in patch.children for p in (*c.incoming, c.outlet)}
    for feature in patch.features:
        if feature.kind == "river":
            for node, surface in zip(feature.nodes, feature.surface_m, strict=True):
                if node.startswith("port:") and node[5:] in ports:
                    assert surface == pytest.approx(ports[node[5:]].surface_m)
    parent = next(
        c for c in patch.children if c.address == fine.CellAddress("flat", 1, *child_address)
    )
    child = fine.refine_patch(base, parent, np.asarray(child_ground))
    assert child.accumulation_m2[child.targets == -1].sum() == pytest.approx(parent.total_area_m2)
    for i, j in enumerate(child.targets):
        if j >= 0:
            assert child.surfaces_m[j] <= child.surfaces_m[i] + 1e-9
