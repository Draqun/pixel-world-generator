"""Bounded world hydrology primitives; enabled project export is not yet available."""

import hashlib
import heapq
import math
from dataclasses import asdict, dataclass, fields

import numpy as np
from numpy.typing import NDArray

from pixel_world.coordinates import FACES
from pixel_world.world import WorldDefinition, canonical_json, finite

FACE_ORDER = ("+x", "-x", "+y", "-y", "+z", "-z")

LIMITS = {
    "backbone_cells": 1_048_576,
    "backbone_vertices": 1_048_576,
    "geometry_vertices": 1_048_576,
    "refinement_patches": 65_536,
    "refinement_windows": 64,
    "cache_bytes": 64 * 1024 * 1024,
}


@dataclass(frozen=True)
class HydrologyDefinition:
    model: str = "none"
    backbone_resolution: int = 64
    finest_cell_span_m: float = 64.0
    max_refinement_depth: int = 16
    min_river_area_m2: float = 1_000_000.0
    min_lake_area_m2: float = 4096.0
    min_lake_depth_m: float = 0.5
    major_river_area_m2: float = 1_000_000_000.0
    major_lake_area_m2: float = 1_000_000.0
    max_channel_width_m: float = 64.0

    def __post_init__(self) -> None:
        if self.model not in ("none", "hierarchical-v1"):
            raise ValueError("unsupported hydrology model; use a compatible generator")
        for name, low, high in (
            ("backbone_resolution", 2, 8192),
            ("max_refinement_depth", 0, 16),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")
        for field in fields(self):
            if field.name in ("model", "backbone_resolution", "max_refinement_depth"):
                continue
            value = getattr(self, field.name)
            finite(value, field.name)
            if value <= 0:
                raise ValueError(f"{field.name} must be positive")
            object.__setattr__(self, field.name, float(value))
        if not 1 <= self.max_channel_width_m <= 64:
            raise ValueError("max_channel_width_m must be in [1, 64] metres")
        if self.major_river_area_m2 < self.min_river_area_m2:
            raise ValueError("major_river_area_m2 must not be below min_river_area_m2")
        if self.major_lake_area_m2 < self.min_lake_area_m2:
            raise ValueError("major_lake_area_m2 must not be below min_lake_area_m2")

    def to_dict(self) -> dict:
        """Expand versioned constants as well as validated settings for canonical serialization."""
        return asdict(self) | {
            "refinement_factor": 4,
            "bank_width_factor": 2,
            "max_bank_span_m": 128,
            "anchor_clearance_m": 1,
            "lake_bank_fraction": 0.0625,
            "width_area_scale_m2": 1_000_000,
            "limits": dict(LIMITS),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HydrologyDefinition":
        """Reject incomplete, future or tampered model definitions without filling defaults."""
        if not isinstance(data, dict) or set(data) != set(cls().to_dict()):
            raise ValueError("incomplete or unknown hydrology definition fields")
        names = {field.name for field in fields(cls)}
        definition = cls(**{name: data[name] for name in sorted(names)})
        if canonical_json(definition.to_dict()) != canonical_json(data):
            raise ValueError("unsupported hydrology constants; use a compatible generator")
        return definition

    def model_id(self, world: WorldDefinition) -> str:
        """Identity excludes coverage, paths and presentation, just like world identity."""
        return hashlib.sha256(
            canonical_json({"world": world.to_dict(), "hydrology": self.to_dict()})
        ).hexdigest()


@dataclass(frozen=True)
class BackboneLayout:
    rows: int
    columns: int
    cells: int
    vertices: int
    depth: int


def backbone_layout(world: WorldDefinition, settings: HydrologyDefinition) -> BackboneLayout:
    """Validate size/depth/vertical budgets arithmetically, without allocating a mesh."""
    if settings.model == "none":
        raise ValueError("hydrology is disabled")
    n = settings.backbone_resolution
    if world.geometry == "sphere":
        rows = columns = n
        cells, vertices = 6 * n * n, 24 * n * n + 2
        span = 2 * world.radius_m / n
        area = 4 * math.pi * world.radius_m * world.radius_m
    else:
        longest = max(world.width_m, world.height_m)
        columns = max(2 if world.boundary == "wrap_x" else 1, round(n * (world.width_m / longest)))
        rows = max(1, round(n * (world.height_m / longest)))
        cells = rows * columns
        vertices = (2 * rows + 1) * (2 * columns if world.boundary == "wrap_x" else 2 * columns + 1)
        span = max(world.width_m / columns, world.height_m / rows)
        area = world.width_m * world.height_m
    if cells > LIMITS["backbone_cells"] or vertices > LIMITS["backbone_vertices"]:
        raise ValueError("backbone exceeds 1048576-cell/vertex budget; lower backbone_resolution")
    if not math.isfinite(area) or area <= 0:
        raise ValueError("world physical area is outside hydrology precision limits")
    depth = 0
    while span > settings.finest_cell_span_m and depth <= settings.max_refinement_depth:
        span /= 4
        depth += 1
    if depth > settings.max_refinement_depth:
        raise ValueError("required refinement depth exceeds limit; reduce world size or detail")
    quantum = world.height_range_m / 65535
    if (
        world.sea_level_m - world.height_min_m < quantum
        or settings.min_lake_depth_m > world.height_range_m
    ):
        raise ValueError("vertical encoding cannot represent the requested submerged water beds")
    return BackboneLayout(rows, columns, cells, vertices, depth)


@dataclass(frozen=True)
class BackboneMesh:
    layout: BackboneLayout
    cell_ids: tuple[str, ...]
    positions: NDArray[np.float64]
    cell_corners: NDArray[np.float64]
    edge_vertices: NDArray[np.int64]
    edge_neighbours: NDArray[np.int64]
    areas_m2: NDArray[np.float64]
    neighbours: tuple[tuple[int, ...], ...]
    boundary: NDArray[np.bool_]
    vertex_ids: tuple[str, ...]
    vertex_positions: NDArray[np.float64]
    vertex_sources: tuple[tuple[int, ...], ...]
    vertex_is_corner: NDArray[np.bool_]
    triangles: NDArray[np.int64]
    triangle_points: NDArray[np.float64]
    geometry: str
    topology: str
    radius_m: float | None


def _mesh_point(
    world: WorldDefinition, layout: BackboneLayout, face: str, u2: int, v2: int
) -> tuple[tuple[int, ...], tuple[float, float, float]]:
    rows, cols = layout.rows, layout.columns
    if world.geometry == "sphere":
        normal, right, down = FACES[face]
        key = tuple(
            normal[i] * (2 * cols) + right[i] * (2 * u2 - 2 * cols) + down[i] * (2 * v2 - 2 * rows)
            for i in range(3)
        )
        length = math.hypot(*key)
        return key, tuple(value / length for value in key)
    key = (u2 % (2 * cols) if world.boundary == "wrap_x" else u2, v2)
    return key, (u2 * world.width_m / (2 * cols), v2 * world.height_m / (2 * rows), 0.0)


def backbone_mesh(world: WorldDefinition, settings: HydrologyDefinition) -> BackboneMesh:
    """Build cell-owned routing budgets and independent, conforming shoreline geometry."""
    layout = backbone_layout(world, settings)
    cell_ids, positions, cell_corners, edge_vertices = [], [], [], []
    keys, vertex_ids, vertex_positions, vertex_sources, vertex_is_corner = {}, [], [], [], []
    triangles, triangle_points = [], []
    faces = FACE_ORDER if world.geometry == "sphere" else ("flat",)

    def vertex(face: str, u2: int, v2: int, cell: int, corner: bool) -> tuple[int, tuple]:
        key, point = _mesh_point(world, layout, face, u2, v2)
        if key not in keys:
            keys[key] = len(vertex_ids)
            vertex_ids.append("vertex:" + ":".join(str(value) for value in key))
            vertex_positions.append(point)
            vertex_sources.append([])
            vertex_is_corner.append(corner)
        index = keys[key]
        vertex_sources[index].append(cell)
        return index, point

    for face in faces:
        for y in range(layout.rows):
            for x in range(layout.columns):
                cell = len(cell_ids)
                cell_ids.append(f"{world.geometry}:{world.boundary}:{face}:0:{x}:{y}")
                centre, position = vertex(face, 2 * x + 1, 2 * y + 1, cell, False)
                positions.append(position)
                ring = [
                    vertex(face, 2 * x + dx, 2 * y + dy, cell, k % 2 == 0)
                    for k, (dx, dy) in enumerate(
                        ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 1))
                    )
                ]
                cell_corners.append([point for _, point in ring[::2]])
                edge_vertices.append([index for index, _ in ring[1::2]])
                for k in range(8):
                    a, b = ring[k], ring[(k + 1) % 8]
                    triangles.append((centre, a[0], b[0]))
                    triangle_points.append((position, a[1], b[1]))
    edge_vertices = np.asarray(edge_vertices, dtype=np.int64)
    edge_neighbours = np.full(edge_vertices.shape, -1, dtype=np.int64)
    for i, edges in enumerate(edge_vertices):
        for k, edge in enumerate(edges):
            other = [j for j in vertex_sources[edge] if j != i]
            if other:
                edge_neighbours[i, k] = other[0]
    corners = np.asarray(cell_corners, dtype=np.float64)
    areas = np.zeros(len(cell_ids), dtype=np.float64)
    for indices in ((0, 1, 2), (0, 2, 3)):
        a, b, c = (corners[:, i] for i in indices)
        if world.geometry == "sphere":
            determinant = np.abs(np.einsum("ij,ij->i", a, np.cross(b, c)))
            denominator = 1 + np.sum(a * b + b * c + c * a, axis=1)
            areas += 2 * np.arctan2(determinant, denominator) * world.radius_m**2
        else:
            areas += np.abs(np.cross(b - a, c - a)[:, 2]) / 2
    return BackboneMesh(
        layout,
        tuple(cell_ids),
        np.asarray(positions),
        corners,
        edge_vertices,
        edge_neighbours,
        areas,
        tuple(tuple(sorted(set(int(j) for j in row if j >= 0))) for row in edge_neighbours),
        (edge_neighbours < 0).any(axis=1),
        tuple(vertex_ids),
        np.asarray(vertex_positions),
        tuple(tuple(sorted(row, key=lambda j: cell_ids[j])) for row in vertex_sources),
        np.asarray(vertex_is_corner, dtype=bool),
        np.asarray(triangles, dtype=np.int64),
        np.asarray(triangle_points, dtype=np.float64),
        world.geometry,
        "sphere" if world.geometry == "sphere" else world.boundary,
        world.radius_m,
    )


@dataclass(frozen=True)
class BackboneDrainage:
    ground_m: NDArray[np.float64]
    sea: NDArray[np.bool_]
    lake: NDArray[np.bool_]
    surface_m: NDArray[np.float64]
    targets: NDArray[np.int64]
    outlet_ports: NDArray[np.int64]
    rank: NDArray[np.int64]
    accumulation_m2: NDArray[np.float64]
    terminal: NDArray[np.bool_]
    ocean_groups: tuple[tuple[int, ...], ...]
    lake_groups: tuple[tuple[int, ...], ...]


def _components(
    mesh: BackboneMesh, mask: NDArray[np.bool_], levels: NDArray[np.float64] | None = None
) -> tuple[tuple[int, ...], ...]:
    seen = np.zeros(len(mesh.cell_ids), dtype=bool)
    groups = []
    for i in sorted(np.flatnonzero(mask), key=lambda i: mesh.cell_ids[i]):
        if seen[i]:
            continue
        seen[i] = True
        queue, group = [int(i)], []
        for j in queue:
            group.append(j)
            for k in mesh.neighbours[j]:
                if mask[k] and not seen[k] and (levels is None or levels[k] == levels[j]):
                    seen[k] = True
                    queue.append(k)
        groups.append(tuple(sorted(group, key=lambda j: mesh.cell_ids[j])))
    return tuple(groups)


def solve_backbone(
    mesh: BackboneMesh,
    ground_m: NDArray,
    sea_level_m: float,
    settings: HydrologyDefinition,
) -> BackboneDrainage:
    """Route a whole bounded graph; only actual world outlets seed priority-flood."""
    finite(sea_level_m, "sea_level_m")
    ground = np.asarray(ground_m)
    size = len(mesh.cell_ids)
    if ground.dtype.kind not in "fiu" or ground.shape != (size,) or not np.isfinite(ground).all():
        raise ValueError("ground must contain one finite elevation per backbone cell")
    ground = ground.astype(np.float64, copy=True)
    below_groups = _components(mesh, ground < sea_level_m)
    ocean_groups = tuple(group for group in below_groups if mesh.boundary[list(group)].any())
    if not ocean_groups and below_groups and mesh.topology != "bounded":
        ocean_groups = (
            min(
                below_groups,
                key=lambda group: (
                    -float(mesh.areas_m2[list(group)].sum()),
                    mesh.cell_ids[group[0]],
                ),
            ),
        )
    sea = np.zeros(size, dtype=bool)
    for group in ocean_groups:
        sea[list(group)] = True
    surface = ground.copy()
    surface[sea] = sea_level_m
    visited = sea | mesh.boundary
    terminal = np.zeros(size, dtype=bool)
    if not visited.any():
        root = min(range(size), key=lambda i: (ground[i], mesh.cell_ids[i]))
        visited[root] = terminal[root] = True
    targets = np.full(size, -1, dtype=np.int64)
    heap = [(float(surface[i]), mesh.cell_ids[i], int(i)) for i in np.flatnonzero(visited)]
    heapq.heapify(heap)
    order = []
    while heap:
        level, _, i = heapq.heappop(heap)
        order.append(i)
        for j in mesh.neighbours[i]:
            if not visited[j]:
                visited[j] = True
                surface[j] = max(level, ground[j])
                targets[j] = i
                heapq.heappush(heap, (float(surface[j]), mesh.cell_ids[j], j))
    if len(order) != size:
        raise ValueError("backbone topology is disconnected from its prescribed roots")
    rank = np.empty(size, dtype=np.int64)
    rank[order] = np.arange(size)
    lake = np.zeros(size, dtype=bool)
    lake_groups = []
    for group in _components(mesh, ~sea & (surface > ground), surface):
        indices = list(group)
        if (
            mesh.areas_m2[indices].sum() >= settings.min_lake_area_m2
            and np.max(surface[indices] - ground[indices]) >= settings.min_lake_depth_m
        ):
            lake[indices] = True
            lake_groups.append(group)
            # One retained lake owns one spill; a multi-source flood can otherwise split it.
            first = min(group, key=lambda i: rank[i])
            members, seen, queue = set(group), {first}, [first]
            for i in queue:
                for j in mesh.neighbours[i]:
                    if j in members and j not in seen:
                        seen.add(j)
                        targets[j] = i
                        queue.append(j)
    children = [[] for _ in range(size)]
    for i, parent in enumerate(targets):
        if parent >= 0:
            children[parent].append(i)
    order = sorted(np.flatnonzero(targets == -1), key=lambda i: mesh.cell_ids[i])
    for i in order:
        order.extend(children[i])
    if len(order) != size:
        raise ValueError("lake spill routing contains a cycle")
    rank[order] = np.arange(size)
    accumulation = mesh.areas_m2.copy()
    for i in reversed(order):
        parent = targets[i]
        if parent >= 0:
            accumulation[parent] += accumulation[i]
    outlet_ports = np.full(size, -1, dtype=np.int64)
    for i, parent in enumerate(targets):
        candidates = np.flatnonzero(mesh.edge_neighbours[i] == parent)
        if (parent >= 0 or (mesh.boundary[i] and not sea[i])) and len(candidates):
            outlet_ports[i] = min(
                (int(mesh.edge_vertices[i, edge]) for edge in candidates),
                key=lambda vertex: mesh.vertex_ids[vertex],
            )
    return BackboneDrainage(
        ground,
        sea,
        lake,
        surface,
        targets,
        outlet_ports,
        rank,
        accumulation,
        terminal,
        ocean_groups,
        tuple(lake_groups),
    )


@dataclass(frozen=True)
class OceanPolygon:
    ocean_id: str
    triangle: int
    vertices: tuple[tuple[float, float, float], ...]


def ocean_polygons(
    mesh: BackboneMesh, drainage: BackboneDrainage, sea_level_m: float
) -> tuple[OceanPolygon, ...]:
    """Clip fixed backbone triangles; regional exports cannot discover ocean connections."""
    cell_owners = [None] * len(mesh.cell_ids)
    for group in drainage.ocean_groups:
        for i in group:
            cell_owners[i] = "sea:" + mesh.cell_ids[group[0]]
    ground = np.asarray(
        [
            max(drainage.ground_m[list(cells)])
            if corner
            else math.fsum(float(drainage.ground_m[i]) for i in cells) / len(cells)
            for cells, corner in zip(mesh.vertex_sources, mesh.vertex_is_corner, strict=True)
        ]
    )
    owners = [
        next((cell_owners[i] for i in cells if cell_owners[i] is not None), None)
        if ground[j] < sea_level_m
        else None
        for j, cells in enumerate(mesh.vertex_sources)
    ]
    polygons, count = [], 0
    for triangle_id, (triangle, points) in enumerate(
        zip(mesh.triangles, mesh.triangle_points, strict=True)
    ):
        wet = [int(i) for i in triangle if owners[i] is not None]
        if not wet:
            continue
        vertices = []
        for edge in range(3):
            i, j = int(triangle[edge - 1]), int(triangle[edge])
            a, b = points[edge - 1], points[edge]
            a_wet, b_wet = ground[i] < sea_level_m, ground[j] < sea_level_m
            if a_wet != b_wet:
                # One arithmetic direction per shared edge avoids orientation-dependent roundoff.
                if i > j:
                    i, j, a, b = j, i, b, a
                fraction = (sea_level_m - ground[i]) / (ground[j] - ground[i])
                point = a + fraction * (b - a)
                if mesh.geometry == "sphere":
                    point = point / np.linalg.norm(point)
                vertices.append(tuple(float(v) for v in point))
            if b_wet:
                vertices.append(tuple(float(v) for v in points[edge]))
        count += len(vertices)
        if count > LIMITS["geometry_vertices"]:
            raise ValueError("ocean geometry exceeds vertex budget; lower backbone_resolution")
        polygons.append(OceanPolygon(owners[wet[0]], triangle_id, tuple(vertices)))
    return tuple(polygons)


@dataclass(frozen=True)
class WaterFeature:
    feature_id: str
    kind: str
    nodes: tuple[str, ...]
    geometry: tuple[tuple[float, float], ...]
    downstream_ids: tuple[str, ...]
    surface_m: tuple[float, ...]
    area_m2: float
    width_m: float = 0.0


def backbone_features(
    mesh: BackboneMesh,
    drainage: BackboneDrainage,
    settings: HydrologyDefinition,
    *,
    vertex_budget: int | None = None,
) -> tuple[WaterFeature, ...]:
    """Give physical waters and true roots stable identities; omit subthreshold dry channels."""
    size = len(mesh.cell_ids)
    owner = [None] * size
    groups = []
    for kind, components in (("sea", drainage.ocean_groups), ("lake", drainage.lake_groups)):
        for members in components:
            feature_id = kind + ":" + mesh.cell_ids[members[0]]
            groups.append((feature_id, kind, members))
            for i in members:
                owner[i] = feature_id
    for i in sorted(range(size), key=lambda i: mesh.cell_ids[i]):
        if owner[i] is not None:
            continue
        if drainage.targets[i] == -1:
            kind = "terminal-basin" if drainage.terminal[i] else "world-outlet"
        elif drainage.accumulation_m2[i] >= settings.min_river_area_m2:
            kind = "river"
        else:
            continue
        owner[i] = kind + ":" + mesh.cell_ids[i]
        groups.append((owner[i], kind, (i,)))
    destination = [None] * size
    for i in np.argsort(drainage.rank):
        destination[i] = owner[i] or destination[drainage.targets[i]]
    features = []
    remaining = LIMITS["geometry_vertices"] if vertex_budget is None else vertex_budget
    for feature_id, kind, members in groups:
        if kind in ("sea", "world-outlet", "terminal-basin"):
            downstream = ()
        elif kind == "lake":
            first = min(members, key=lambda i: drainage.rank[i])
            parent = drainage.targets[first]
            downstream = (destination[parent],) if parent >= 0 else ()
        else:
            downstream = (destination[drainage.targets[members[0]]],)
        indices = members
        width = 0.0
        if kind == "river":
            i = members[0]
            indices = (i, int(drainage.targets[i]))
            area = float(drainage.accumulation_m2[i])
            width = min(settings.max_channel_width_m, max(1.0, math.sqrt(area / 1_000_000)))
        elif kind in ("world-outlet", "terminal-basin"):
            area = float(drainage.accumulation_m2[members[0]])
        else:
            area = float(mesh.areas_m2[list(members)].sum())
        route_points = [mesh.positions[i] for i in indices]
        route_ids = [mesh.cell_ids[i] for i in indices]
        surfaces = [float(drainage.surface_m[i]) for i in indices]
        if kind in ("river", "world-outlet"):
            port = int(drainage.outlet_ports[members[0]])
            route_points.insert(1, mesh.vertex_positions[port])
            route_ids.insert(1, mesh.vertex_ids[port])
            surfaces.insert(1, (surfaces[0] + surfaces[-1]) / 2)
        remaining -= len(route_points)
        if remaining < 0:
            raise ValueError(
                "water feature geometry exceeds vertex budget; lower backbone_resolution"
            )
        geometry = []
        for a, b, c in route_points:
            if mesh.geometry == "sphere":
                a, b = (
                    (math.degrees(math.atan2(b, a)) + 180) % 360 - 180,
                    math.degrees(math.atan2(c, math.hypot(a, b))),
                )
                if abs(b) == 90:
                    a = 0.0
            geometry.append((float(a), float(b)))
        features.append(
            WaterFeature(
                feature_id,
                kind,
                tuple(route_ids),
                tuple(geometry),
                downstream,
                tuple(surfaces),
                area,
                width,
            )
        )
    return tuple(sorted(features, key=lambda feature: feature.feature_id))


@dataclass(frozen=True)
class WorldBackbone:
    world: WorldDefinition
    settings: HydrologyDefinition
    mesh: BackboneMesh
    drainage: BackboneDrainage
    oceans: tuple[OceanPolygon, ...]
    features: tuple[WaterFeature, ...]

    @property
    def model_id(self) -> str:
        return self.settings.model_id(self.world)

    def to_dict(self) -> dict:
        """Canonical internal snapshot, not a claim of finished regional water output."""
        return {
            "format": "internal-backbone-v1",
            "seed": self.world.seed,
            "generator_version": self.world.generator_version,
            "world_id": self.world.world_id,
            "world": self.world.to_dict(),
            "model_id": self.model_id,
            "parameters": self.settings.to_dict(),
            "topology": self.mesh.topology,
            "refinement_depth": self.mesh.layout.depth,
            "exact_global_drainage": False,
            "area_units": "m2; estimated terrain catchments on the backbone graph",
            "position_units": "unit sphere vectors"
            if self.world.geometry == "sphere"
            else "metres",
            "feature_position_units": "longitude/latitude degrees"
            if self.world.geometry == "sphere"
            else "metres",
            "cell_ids": self.mesh.cell_ids,
            "vertex_ids": self.mesh.vertex_ids,
            "vertex_positions": self.mesh.vertex_positions.tolist(),
            "cell_corners": self.mesh.cell_corners.tolist(),
            "edge_vertices": self.mesh.edge_vertices.tolist(),
            "positions": self.mesh.positions.tolist(),
            "triangles": self.mesh.triangles.tolist(),
            "areas_m2": self.mesh.areas_m2.tolist(),
            "ground_m": self.drainage.ground_m.tolist(),
            "surface_m": self.drainage.surface_m.tolist(),
            "targets": self.drainage.targets.tolist(),
            "outlet_ports": self.drainage.outlet_ports.tolist(),
            "edge_neighbours": self.mesh.edge_neighbours.tolist(),
            "rank": self.drainage.rank.tolist(),
            "accumulation_m2": self.drainage.accumulation_m2.tolist(),
            "ocean_polygons": [asdict(polygon) for polygon in self.oceans],
            "features": [asdict(feature) for feature in self.features],
        }


def generate_backbone(world: WorldDefinition, settings: HydrologyDefinition) -> WorldBackbone:
    """Sample the saved coarse geography and solve the complete bounded graph, without I/O."""
    from pixel_world.overview import geography_field
    from pixel_world.seeds import step_rng

    mesh = backbone_mesh(world, settings)
    if world.geometry == "sphere":
        x, y, z = mesh.positions.T
        first = np.rad2deg(np.arctan2(y, x))
        second = np.rad2deg(np.arctan2(z, np.hypot(x, y)))
        first = np.where(abs(second) == 90, 0, first)
    else:
        first = np.minimum(mesh.positions[:, 0], np.nextafter(world.width_m, 0))
        second = np.minimum(mesh.positions[:, 1], np.nextafter(world.height_m, 0))
    # Hydrology routes the existing geography; the solver itself is deterministic and RNG-free.
    height = geography_field(world, first, second, step_rng(world.seed, "world.geography"))
    ground = world.height_min_m + height * world.height_range_m
    drainage = solve_backbone(mesh, ground, world.sea_level_m, settings)
    oceans = ocean_polygons(mesh, drainage, world.sea_level_m)
    remaining = LIMITS["geometry_vertices"] - sum(len(p.vertices) for p in oceans)
    features = backbone_features(mesh, drainage, settings, vertex_budget=remaining)
    return WorldBackbone(world, settings, mesh, drainage, oceans, features)
