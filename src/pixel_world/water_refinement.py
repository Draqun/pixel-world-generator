"""Canonical, bounded refinement of the internal world-water model; no export I/O."""

import heapq
import math
from dataclasses import asdict, dataclass, replace
from fractions import Fraction

import numpy as np
from numpy.typing import NDArray

from pixel_world.coordinates import FACES
from pixel_world.seeds import step_rng
from pixel_world.world import WorldDefinition, finite
from pixel_world.world_water import LIMITS, HydrologyDefinition, WaterFeature, WorldBackbone


@dataclass(frozen=True, order=True)
class CellAddress:
    face: str
    level: int
    x: int
    y: int

    def __post_init__(self) -> None:
        if self.face not in ("flat", "+x", "-x", "+y", "-y", "+z", "-z"):
            raise ValueError("unknown hydrology face")
        if (
            any(type(v) is not int or v < 0 for v in (self.level, self.x, self.y))
            or self.level > 16
        ):
            raise ValueError("invalid hydrology cell address")

    @property
    def key(self) -> str:
        return f"{self.face}:{self.level}:{self.x}:{self.y}"

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        scale = 4**self.level
        return self.x / scale, self.y / scale, (self.x + 1) / scale, (self.y + 1) / scale


@dataclass(frozen=True)
class FlowPort:
    port_id: str
    position: tuple[float, float, float]
    surface_m: float
    area_m2: float


@dataclass(frozen=True)
class RefinedFeature(WaterFeature):
    parent_id: str = ""
    outlet_geometry: tuple[tuple[float, float], ...] = ()
    outlet_surface_m: tuple[float, ...] = ()
    outlet_feature_id: str | None = None


@dataclass(frozen=True)
class WaterFootprint:
    feature_id: str
    kind: str
    vertices: tuple[tuple[float, float, float], ...]
    surface_m: float
    parent_id: str


def _world_position(base: WorldBackbone, point: tuple) -> tuple[float, float]:
    a, b, c = point
    if base.world.geometry == "sphere":
        return (
            (math.degrees(math.atan2(b, a)) + 180) % 360 - 180,
            math.degrees(math.atan2(c, math.hypot(a, b))),
        )
    return float(a), float(b)


def _project(
    base: WorldBackbone, address: CellAddress, points: tuple, *, directions: bool = False
) -> tuple:
    result = []
    x0, y0, x1, y1 = address.bounds
    for point in points:
        if base.world.geometry == "sphere":
            if directions:
                direction = point
            else:
                lon, lat = map(math.radians, point)
                direction = (
                    math.cos(lat) * math.cos(lon),
                    math.cos(lat) * math.sin(lon),
                    math.sin(lat),
                )
            normal, right, down = FACES[address.face]
            denominator = sum(a * b for a, b in zip(direction, normal, strict=True))
            if denominator <= 0:
                return ()
            u = (
                base.mesh.layout.columns
                * (1 + sum(a * b for a, b in zip(direction, right, strict=True)) / denominator)
                / 2
            )
            v = (
                base.mesh.layout.rows
                * (1 + sum(a * b for a, b in zip(direction, down, strict=True)) / denominator)
                / 2
            )
        else:
            u, v = (
                point[0] / base.world.width_m * base.mesh.layout.columns,
                point[1] / base.world.height_m * base.mesh.layout.rows,
            )
            if base.world.boundary == "wrap_x":
                u += (
                    round(((x0 + x1) / 2 - u) / base.mesh.layout.columns) * base.mesh.layout.columns
                )
        result.append(((u - x0) / (x1 - x0), (v - y0) / (y1 - y0)))
    return tuple(result)


def _box_segment(a: tuple, b: tuple, bounds: tuple = (0.0, 0.0, 1.0, 1.0)) -> bool:
    low, high = 0.0, 1.0
    for p, q, minimum, maximum in zip(a, b, bounds[:2], bounds[2:], strict=True):
        delta = q - p
        if delta == 0:
            if not minimum <= p <= maximum:
                return False
        else:
            x, y = (minimum - p) / delta, (maximum - p) / delta
            low, high = max(low, min(x, y)), min(high, max(x, y))
            if low > high:
                return False
    return True


def _intersects(base: WorldBackbone, address: CellAddress, feature: WaterFeature) -> bool:
    points = _feature_native(base, address, feature)
    span = 1 / 4**address.level
    radius = feature.width_m / 2 if feature.kind == "river" else 0.0
    if base.world.geometry == "sphere":
        dx = dy = (
            radius * 3 * math.sqrt(3) * base.mesh.layout.columns / (2 * base.world.radius_m * span)
        )
    else:
        dx = radius * base.mesh.layout.columns / (base.world.width_m * span)
        dy = radius * base.mesh.layout.rows / (base.world.height_m * span)
    bounds = (-dx, -dy, 1 + dx, 1 + dy)
    return bool(points) and (
        any(bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3] for x, y in points)
        or any(_box_segment(a, b, bounds) for a, b in zip(points[:-1], points[1:], strict=True))
    )


def _footprint_intersects(
    base: WorldBackbone, address: CellAddress, footprint: WaterFootprint
) -> bool:
    points = _project(base, address, footprint.vertices, directions=True)
    if not points:
        return False
    if any(_box_segment(a, b) for a, b in zip(points, points[1:] + points[:1], strict=True)):
        return True
    # Convex footprint facets can wholly contain the cell.
    signs = [
        (b[0] - a[0]) * (0.5 - a[1]) - (b[1] - a[1]) * (0.5 - a[0])
        for a, b in zip(points, points[1:] + points[:1], strict=True)
    ]
    return all(s >= 0 for s in signs) or all(s <= 0 for s in signs)


def _clip_facet(
    base: WorldBackbone, triangle: NDArray, points: NDArray, ground: NDArray, level: float
) -> tuple:
    vertices = []
    for edge in range(3):
        i, j = int(triangle[edge - 1]), int(triangle[edge])
        a, b = points[edge - 1], points[edge]
        wet_a, wet_b = ground[i] < level, ground[j] < level
        if wet_a != wet_b:
            if i > j:
                i, j, a, b = j, i, b, a
            point = a + (level - ground[i]) / (ground[j] - ground[i]) * (b - a)
            if base.world.geometry == "sphere":
                point = point / np.linalg.norm(point)
            vertices.append(tuple(map(float, point)))
        if wet_b:
            vertices.append(tuple(map(float, points[edge])))
    return tuple(vertices)


def _root_footprints(base: WorldBackbone) -> tuple[tuple[WaterFootprint, ...], ...]:
    mesh, d = base.mesh, base.drainage
    result = [[] for _ in mesh.cell_ids]
    count = sum(len(f.geometry) for f in base.features)
    for polygon in base.oceans:
        owner = polygon.triangle // 8
        result[owner].append(
            WaterFootprint(
                polygon.ocean_id,
                "sea",
                polygon.vertices,
                base.world.sea_level_m,
                mesh.cell_ids[owner],
            )
        )
        count += len(polygon.vertices)
    if d.lake_groups:
        labels = {i: number for number, group in enumerate(d.lake_groups) for i in group}
        ground = np.asarray(
            [
                max(d.ground_m[list(cells)])
                if corner
                else math.fsum(float(d.ground_m[i]) for i in cells) / len(cells)
                for cells, corner in zip(mesh.vertex_sources, mesh.vertex_is_corner, strict=True)
            ]
        )
        for k, (triangle, points) in enumerate(
            zip(mesh.triangles, mesh.triangle_points, strict=True)
        ):
            groups = {
                labels[i] for vertex in triangle for i in mesh.vertex_sources[vertex] if i in labels
            }
            for number in sorted(
                groups, key=lambda number: mesh.cell_ids[d.lake_groups[number][0]]
            ):
                group = d.lake_groups[number]
                level = float(d.surface_m[group[0]])
                if not any(
                    ground[vertex] < level
                    and any(labels.get(i) == number for i in mesh.vertex_sources[vertex])
                    for vertex in triangle
                ):
                    continue
                vertices = _clip_facet(base, triangle, points, ground, level)
                if len(vertices) >= 3:
                    count += len(vertices)
                    if count > LIMITS["geometry_vertices"]:
                        raise ValueError("inherited water geometry exceeds vertex budget")
                    result[k // 8].append(
                        WaterFootprint(
                            "lake:" + mesh.cell_ids[group[0]],
                            "lake",
                            vertices,
                            level,
                            mesh.cell_ids[k // 8],
                        )
                    )
    if count > LIMITS["geometry_vertices"]:
        raise ValueError("inherited water geometry exceeds vertex budget")
    return tuple(tuple(row) for row in result)


def _segment_interval(a: tuple, b: tuple, bounds: tuple = (0.0, 0.0, 1.0, 1.0)) -> tuple | None:
    low, high = 0.0, 1.0
    for p, q, minimum, maximum in zip(a, b, bounds[:2], bounds[2:], strict=True):
        delta = q - p
        if delta == 0:
            if p < minimum or p > maximum:
                return None
        else:
            x, y = (minimum - p) / delta, (maximum - p) / delta
            low, high = max(low, min(x, y)), min(high, max(x, y))
            if low > high:
                return None
    return low, high


def _feature_native(base: WorldBackbone, address: CellAddress, feature: WaterFeature) -> tuple:
    points = []
    for node in feature.nodes:
        if node.startswith("port:"):
            identity = node[5:]
        elif node.startswith("vertex:"):
            values = tuple(map(int, node.split(":")[1:]))
            if base.world.geometry == "sphere":
                divisor = math.gcd(*values)
                identity = "sphere:" + ":".join(str(v // divisor) for v in values)
            else:
                identity, _ = _point(base, "flat", values[0] / 2, values[1] / 2)
        elif len(node.split(":")) == 6:
            _, _, face, level, x, y = node.split(":")
            cell = CellAddress(face, int(level), int(x), int(y))
            identity = flow_port(base, cell, 0.5, 0.5, 0.0, 0.0).port_id
        else:
            return _project(base, address, feature.geometry)
        u, v = _native(base, address, FlowPort(identity, (0.0, 0.0, 0.0), 0.0, 0.0))
        x0, y0, x1, y1 = address.bounds
        points.append(((u - x0) / (x1 - x0), (v - y0) / (y1 - y0)))
    if base.world.geometry == "flat" and base.world.boundary == "wrap_x" and points:
        x0, y0, x1, y1 = address.bounds
        period = base.mesh.layout.columns / (x1 - x0)
        continuous = [points[0]]
        for u, v in points[1:]:
            u += round((continuous[-1][0] - u) / period) * period
            continuous.append((u, v))
        centre = (min(u for u, v in continuous) + max(u for u, v in continuous)) / 2
        shift = round((0.5 - centre) / period) * period
        points = [(u + shift, v) for u, v in continuous]
    return tuple(points)


def _surface_profile(
    base: WorldBackbone, address: CellAddress, point: tuple, footprints: tuple
) -> float | None:
    """Sample the authoritative wet surface at an interface, with sea/lake precedence."""
    planes = []
    for shape in footprints:
        polygon = _project(base, address, shape.vertices, directions=True)
        if not polygon:
            continue
        signs = [
            (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])
            for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True)
        ]
        if all(v >= -1e-12 for v in signs) or all(v <= 1e-12 for v in signs):
            planes.append((0 if shape.kind == "sea" else 1, shape.feature_id, shape.surface_m))
    return min(planes)[2] if planes else None


def _forced_routes(
    base: WorldBackbone, parent: "CellState", root: int
) -> tuple[dict, dict, dict, dict]:
    targets, ports, caps, edges = {}, {}, {}, {}
    for feature in parent.inherited:
        if feature.kind not in ("river", "world-outlet"):
            continue
        if any(
            not (node.startswith(("port:", "vertex:")) or len(node.split(":")) == 6)
            for node in feature.nodes
        ):
            continue
        points = _feature_native(base, parent.address, feature)
        root_hit = None
        for k, (a, b) in enumerate(zip(points[:-1], points[1:], strict=True)):
            if root_hit is not None:
                break
            root_hit = None
            clipped = _segment_interval(a, b)
            if clipped is None or clipped[1] - clipped[0] < 1e-12:
                continue
            x0, y0, x1, y1 = parent.address.bounds
            out_u, out_v = _native(base, parent.address, parent.outlet)
            out = ((out_u - x0) / (x1 - x0), (out_v - y0) / (y1 - y0))
            root_hit = _intersection(a, b, out, out)
            if root_hit is not None:
                clipped = (clipped[0], min(clipped[1], root_hit[0]))
            on_boundary = any(
                abs(a[d] - edge) < 1e-12 and abs(b[d] - edge) < 1e-12
                for d in (0, 1)
                for edge in (0.0, 1.0)
            )
            if on_boundary:
                carries_input = False
                for incoming in parent.incoming:
                    u, v = _native(base, parent.address, incoming)
                    entry = ((u - x0) / (x1 - x0), (v - y0) / (y1 - y0))
                    hit = _intersection(a, b, entry, entry)
                    if hit is not None:
                        datum = feature.surface_m[k] + hit[0] * (
                            feature.surface_m[k + 1] - feature.surface_m[k]
                        )
                        if math.isclose(incoming.surface_m, datum, abs_tol=1e-8):
                            carries_input = True
                if not carries_input:
                    continue
            if clipped[1] - clipped[0] < 1e-12:
                continue
            start, end = clipped
            for t in (start, end):
                uv = tuple(a[d] + t * (b[d] - a[d]) for d in range(2))
                owner = min(3, max(0, math.floor(4 * uv[1]))) * 4 + min(
                    3, max(0, math.floor(4 * uv[0]))
                )
                level = float(
                    feature.surface_m[k] + t * (feature.surface_m[k + 1] - feature.surface_m[k])
                )
                actual = _surface_profile(base, parent.address, uv, parent.footprints)
                level = level if actual is None else actual
                caps[owner] = min(caps.get(owner, math.inf), level)
            for i in range(16):
                for j in _neighbours(i):
                    if i >= j:
                        continue
                    point = ((i % 4 + j % 4 + 1) / 8, (i // 4 + j // 4 + 1) / 8)
                    hit = _intersection(a, b, point, point)
                    if hit is not None and start - 1e-12 <= hit[0] <= end + 1e-12:
                        datum = feature.surface_m[k] + hit[0] * (
                            feature.surface_m[k + 1] - feature.surface_m[k]
                        )
                        actual = _surface_profile(base, parent.address, point, parent.footprints)
                        datum = float(datum if actual is None else actual)
                        edges[i, j] = edges[j, i] = datum
            times = {start, end}
            for axis in range(2):
                if b[axis] != a[axis]:
                    times.update(
                        t
                        for q in range(1, 4)
                        if start < (t := (q / 4 - a[axis]) / (b[axis] - a[axis])) < end
                    )
            times = sorted(times)
            samples = []
            for left, right in zip(times[:-1], times[1:], strict=True):
                if not samples:
                    samples.append((left, True))
                samples.extend((((left + right) / 2, False), (right, True)))
            previous = None
            for t, is_vertex in samples:
                point = tuple(a[d] + t * (b[d] - a[d]) for d in range(2))
                point = tuple(
                    round(v * 4) / 4 if abs(v * 4 - round(v * 4)) < 1e-8 else v for v in point
                )
                owner = min(3, max(0, math.floor(4 * point[1]))) * 4 + min(
                    3, max(0, math.floor(4 * point[0]))
                )
                if previous is not None and previous[0] != owner:
                    old, old_t = previous
                    boundary = t if is_vertex else old_t
                    uv = tuple(a[d] + boundary * (b[d] - a[d]) for d in range(2))
                    surface = feature.surface_m[k] + boundary * (
                        feature.surface_m[k + 1] - feature.surface_m[k]
                    )
                    if old != root:
                        if old in targets and targets[old] != owner:
                            raise ValueError(
                                "inherited channels require incompatible child outlets"
                            )
                        targets[old] = owner
                        actual = _surface_profile(base, parent.address, uv, parent.footprints)
                        ports[old] = (uv, float(surface if actual is None else actual))
                previous = (owner, t)
    return targets, ports, caps, edges


def _complete_inlets(
    forced: dict,
    locked: dict,
    caps: dict,
    raw: NDArray,
    root: int,
    priorities: NDArray,
    root_level: float,
    edges: dict,
    outlet_uv: tuple,
) -> None:
    """Connect low prescribed inlets without crossing a higher immutable carrier."""
    terminal_edges = {
        i
        for i in _neighbours(root)
        if max(i % 4, root % 4) / 4 - 1e-12
        <= outlet_uv[0]
        <= (min(i % 4, root % 4) + 1) / 4 + 1e-12
        and max(i // 4, root // 4) / 4 - 1e-12
        <= outlet_uv[1]
        <= (min(i // 4, root // 4) + 1) / 4 + 1e-12
    }
    for limit, source in sorted((value, i) for i, value in caps.items()):
        if limit + 1e-9 < root_level:
            raise ValueError("inherited inlet lies below the prescribed outlet")
        queue = [(0.0, 0, int(priorities[source]), source)]
        costs = {source: 0.0}
        previous = {}
        while queue:
            cost, hops, _, i = heapq.heappop(queue)
            if cost != costs[i]:
                continue
            if i == root:
                break
            if i in locked and locked[i][1] > limit + 1e-9:
                continue
            adjacent = (forced[i],) if i in forced else _neighbours(i)
            for j in adjacent:
                boundary = locked[i][1] if i in locked else edges.get((i, j), -math.inf)
                if boundary > limit + 1e-9 and not (
                    j == root and i in terminal_edges and i not in locked
                ):
                    continue
                if j in locked and locked[j][1] > limit + 1e-9:
                    continue
                candidate = cost + 1 + max(0.0, float(raw[j]) - limit)
                if candidate < costs.get(j, math.inf):
                    costs[j] = candidate
                    previous[j] = i
                    heapq.heappush(queue, (candidate, hops + 1, int(priorities[j]), j))
        if root != source and root not in previous:
            raise ValueError("inherited inlet cannot reach its prescribed outlet")
        path = [root]
        while path[-1] != source:
            path.append(previous[path[-1]])
        path.reverse()
        for i, j in zip(path[:-1], path[1:], strict=True):
            if (
                j == root
                and i in terminal_edges
                and i not in locked
                and edges.get((i, j), -math.inf) > limit + 1e-9
            ):
                locked[i] = (outlet_uv, root_level)
            forced.setdefault(i, j)
            caps[i] = min(caps.get(i, math.inf), limit)
        caps[root] = min(caps.get(root, math.inf), limit)


def _wet_mask(base: WorldBackbone, parent: "CellState", addresses: tuple) -> NDArray:
    return np.asarray(
        [
            any(_footprint_intersects(base, a, p) for p in parent.footprints)
            or any(
                f.kind in ("river", "world-outlet") and _intersects(base, a, f)
                for f in parent.inherited
            )
            for a in addresses
        ]
    )


def _lake_groups(
    base: WorldBackbone,
    parent: "CellState",
    addresses: tuple,
    areas: NDArray,
    raw: NDArray,
    surfaces: NDArray,
    imported: NDArray,
) -> tuple:
    candidates = ~_wet_mask(base, parent, addresses) & (
        surfaces - raw >= base.settings.min_lake_depth_m
    )
    groups, seen = [], set()
    for i in range(16):
        if not candidates[i] or i in seen:
            continue
        queue, group = [i], []
        seen.add(i)
        for j in queue:
            group.append(j)
            for k in _neighbours(j):
                if candidates[k] and k not in seen and surfaces[k] == surfaces[i]:
                    seen.add(k)
                    queue.append(k)
        if math.fsum(areas[group]) >= base.settings.min_lake_area_m2 and not np.any(
            imported[group] > 0
        ):
            groups.append(tuple(group))
    return tuple(groups)


def _intersection(a: tuple, b: tuple, c: tuple, d: tuple) -> tuple | None:
    dx, dy = b[0] - a[0], b[1] - a[1]
    ex, ey = d[0] - c[0], d[1] - c[1]
    denominator = dx * ey - dy * ex
    if abs(denominator) < 1e-14:
        if abs((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) > 1e-12:
            return None
        axis = 0 if abs(dx) >= abs(dy) else 1
        delta = b[axis] - a[axis]
        if delta == 0:
            return None
        low, high = sorted(((c[axis] - a[axis]) / delta, (d[axis] - a[axis]) / delta))
        if max(low, 0.0) <= min(high, 1.0):
            t = max(low, 0.0)
            p = (a[0] + t * dx, a[1] + t * dy)
            e = ex if axis == 0 else ey
            u = (p[axis] - c[axis]) / e if e else 0.0
            return t, u
        return None
    t = ((c[0] - a[0]) * ey - (c[1] - a[1]) * ex) / denominator
    u = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / denominator
    return (
        (max(0.0, min(1.0, t)), max(0.0, min(1.0, u)))
        if -1e-10 <= t <= 1 + 1e-10 and -1e-10 <= u <= 1 + 1e-10
        else None
    )


def _channel_preserves_inlets(
    base: WorldBackbone,
    patch: "RefinementPatch",
    feature: RefinedFeature,
    receivers: tuple,
    shapes: tuple,
) -> bool:
    """Reject a new carrier that separates a known lower inlet from its prescribed outlet."""
    for child in patch.children:
        if child.address.level >= base.mesh.layout.depth or not _intersects(
            base, child.address, feature
        ):
            continue
        context = replace(
            child,
            inherited=tuple(
                f
                for f in (*receivers, feature)
                if f.kind != "river" or _intersects(base, child.address, f)
            ),
            footprints=tuple(p for p in shapes if _footprint_intersects(base, child.address, p)),
        )
        try:
            _routing_constraints(base, context, np.zeros(16))
        except ValueError:
            return False
    return True


def _route_channel(
    base: WorldBackbone,
    patch: "RefinementPatch",
    source: int,
    feature_id: str,
    receivers: tuple,
    shapes: tuple,
    *,
    spill: bool = False,
    spill_start: FlowPort | None = None,
) -> RefinedFeature | None:
    parent = patch.parent
    area = float(patch.accumulation_m2[source])
    profiles = [
        (f, _feature_native(base, parent.address, f))
        for f in receivers
        if f.kind in ("river", "world-outlet")
    ]
    polygons = [(p, _project(base, parent.address, p.vertices, directions=True)) for p in shapes]

    def centre(i: int) -> FlowPort:
        return flow_port(base, patch.children[i].address, 0.5, 0.5, 0.0, 0.0)

    ports = [spill_start or patch.children[source].outlet] if spill else [centre(source)]
    levels = [float(patch.surfaces_m[source])]
    i = source
    while i >= 0:
        exit_port = patch.children[i].outlet
        start = ports[-1]
        a, b = _native(base, parent.address, start), _native(base, parent.address, exit_port)
        # Explicit orthogonal turns keep inherited geometry compatible with further 4x4 splits.
        if a[0] != b[0] and a[1] != b[1]:
            x0, y0, x1, y1 = parent.address.bounds
            bend = flow_port(
                base, parent.address, (b[0] - x0) / (x1 - x0), (a[1] - y0) / (y1 - y0), 0.0, 0.0
            )
            ports.append(bend)
            levels.append(levels[-1])
        if ports[-1].port_id != exit_port.port_id:
            ports.append(exit_port)
            levels.append(min(levels[-1], exit_port.surface_m))
        j = int(patch.targets[i])
        if j >= 0:
            ports.append(centre(j))
            levels.append(max(float(patch.surfaces_m[j]), levels[-1]))
        i = j
    # New geometry must carry the already assigned datum at every transport point it crosses.
    prescribed = {p.port_id: p for c in patch.children for p in (*c.incoming, c.outlet)}
    levels = [
        prescribed[p.port_id].surface_m if p.port_id in prescribed else level
        for p, level in zip(ports, levels, strict=True)
    ]
    coupled_ports, coupled_levels = [ports[0]], [levels[0]]
    for a, b, level in zip(ports[:-1], ports[1:], levels[1:], strict=True):
        start, end = _native(base, parent.address, a), _native(base, parent.address, b)
        contacts = []
        for port in prescribed.values():
            point = _native(base, parent.address, port)
            hit = _intersection(start, end, point, point)
            if hit is not None and 1e-10 < hit[0] < 1 - 1e-10:
                contacts.append((hit[0], port.port_id, port))
        for _, _, port in sorted(contacts):
            coupled_ports.append(port)
            coupled_levels.append(port.surface_m)
        coupled_ports.append(b)
        coupled_levels.append(level)
    ports, levels = coupled_ports, coupled_levels
    points = []
    x0, y0, x1, y1 = parent.address.bounds
    for port in ports:
        u, v = _native(base, parent.address, port)
        points.append(((u - x0) / (x1 - x0), (v - y0) / (y1 - y0)))
    for segment, (a, b) in enumerate(zip(points[:-1], points[1:], strict=True)):
        hits = []
        for target, path in profiles:
            for k, (c, d) in enumerate(zip(path[:-1], path[1:], strict=True)):
                hit = _intersection(a, b, c, d)
                if hit is not None:
                    t, u = hit
                    level = target.surface_m[k] + u * (
                        target.surface_m[k + 1] - target.surface_m[k]
                    )
                    hits.append((t, target.feature_id, float(level), target, k, u))
        for shape, path in polygons:
            for c, d in zip(path, path[1:] + path[:1], strict=True):
                hit = _intersection(a, b, c, d)
                if hit is not None:
                    hits.append((hit[0], shape.feature_id, shape.surface_m, None, 0, 0.0))
        if not hits:
            continue
        t, identity, level, target, k, u = min(hits, key=lambda h: (h[0], h[1]))
        if target is not None and target.kind == "river" and area > target.area_m2 * (1 + 1e-12):
            return None
        endpoint = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        end = flow_port(base, parent.address, endpoint[0], endpoint[1], level, area)
        owner = _owner(base, parent, end)
        # A physical contact must not introduce a lower sink than the prescribed transport.
        if level + 1e-9 < patch.children[owner].outlet.surface_m:
            return None
        selected = ports[: segment + 1] + [end]
        selected_levels = levels[: segment + 1] + [level]
        if any(
            a + 1e-9 < b for a, b in zip(selected_levels[:-1], selected_levels[1:], strict=True)
        ):
            return None
        # Reuse the recipient's exact endpoint bytes when the join is a recorded vertex.
        geometry = [_world_position(base, p.position) for p in selected]
        if target is not None and (u == 0 or u == 1):
            geometry[-1] = target.geometry[k + (u == 1)]
        node_ids = ["port:" + p.port_id for p in selected]
        if target is not None and target.kind == "world-outlet":
            geometry.extend(target.geometry[k + 1 :])
            selected_levels.extend(target.surface_m[k + 1 :])
            node_ids.extend(target.nodes[k + 1 :])
        feature = RefinedFeature(
            feature_id,
            "river",
            tuple(node_ids),
            tuple(geometry),
            (identity,),
            tuple(selected_levels),
            area,
            min(base.settings.max_channel_width_m, max(1.0, math.sqrt(area / 1_000_000))),
            parent.address.key,
        )
        return (
            feature if _channel_preserves_inlets(base, patch, feature, receivers, shapes) else None
        )
    # A terminal basin can be a point rather than a positive-depth lake.
    terminal = next((f for f in parent.inherited if f.kind == "terminal-basin"), None)
    if terminal is not None and ports[-1].port_id == parent.outlet.port_id:
        feature = RefinedFeature(
            feature_id,
            "river",
            tuple("port:" + p.port_id for p in ports),
            tuple(_world_position(base, p.position) for p in ports),
            (terminal.feature_id,),
            tuple(levels),
            area,
            min(base.settings.max_channel_width_m, max(1.0, math.sqrt(area / 1_000_000))),
            parent.address.key,
        )
        return (
            feature if _channel_preserves_inlets(base, patch, feature, receivers, shapes) else None
        )
    return None


def _polygon_area(base: WorldBackbone, vertices: tuple) -> float:
    a, b, c, d = map(np.asarray, vertices)
    total = 0.0
    for p, q, r in ((a, b, c), (a, c, d)):
        if base.world.geometry == "sphere":
            total += (
                2
                * math.atan2(
                    abs(float(np.dot(p, np.cross(q, r)))),
                    1 + float(np.dot(p, q) + np.dot(q, r) + np.dot(r, p)),
                )
                * base.world.radius_m**2
            )
        else:
            total += abs(float(np.cross(q - p, r - p)[2])) / 2
    return total


def _new_lake_geometry(
    base: WorldBackbone, patch: "RefinementPatch", group: tuple, identity: str
) -> tuple:
    """Reserve dry banks around a new basin, keeping canonical interfaces outside its surface."""
    members = set(group)
    bank = base.settings.to_dict()["lake_bank_fraction"]
    shapes, area = [], 0.0
    source = min(group, key=lambda j: patch.rank[j])
    shore = None
    for j in group:
        address = patch.children[j].address
        x, y = j % 4, j // 4
        left = 0.0 if x > 0 and j - 1 in members else bank
        right = 1.0 if x < 3 and j + 1 in members else 1 - bank
        top = 0.0 if y > 0 and j - 4 in members else bank
        bottom = 1.0 if y < 3 and j + 4 in members else 1 - bank
        vertices = tuple(
            flow_port(base, address, u, v, 0.0, 0.0).position
            for u, v in ((left, top), (right, top), (right, bottom), (left, bottom))
        )
        area += _polygon_area(base, vertices)
        shapes.append(
            WaterFootprint(
                identity, "lake", vertices, float(patch.surfaces_m[j]), patch.parent.address.key
            )
        )
        if j == source:
            u, v = _native(base, address, patch.children[j].outlet)
            x0, y0, x1, y1 = address.bounds
            u, v = (u - x0) / (x1 - x0), (v - y0) / (y1 - y0)
            if u < 0.5:
                u, v = left, 0.5
            elif u > 0.5:
                u, v = right, 0.5
            else:
                u, v = 0.5, top if v < 0.5 else bottom
            shore = flow_port(
                base, address, u, v, float(patch.surfaces_m[j]), float(patch.accumulation_m2[j])
            )
    return tuple(shapes), area, shore


def _local_features(base: WorldBackbone, patch: "RefinementPatch") -> tuple[tuple, tuple]:
    parent, children = patch.parent, patch.children
    addresses = tuple(c.address for c in children)
    wet = _wet_mask(base, parent, addresses)
    groups = _lake_groups(
        base,
        parent,
        addresses,
        patch.local_areas_m2,
        patch.ground_m,
        patch.surfaces_m,
        patch.imported_accumulation_m2,
    )
    features, footprints = [], []
    lake_at = {i: group for group in groups for i in group}
    completed = set()
    inherited = {f.feature_id: f for f in parent.inherited}
    if parent.anchor is not None:
        inherited[parent.anchor.feature_id] = parent.anchor
    for i in np.argsort(patch.rank):
        i = int(i)
        receivers = tuple(inherited[key] for key in sorted(inherited)) + tuple(features)
        if i in lake_at:
            group = lake_at[i]
            if group in completed:
                continue
            completed.add(group)
            source = min(group, key=lambda j: patch.rank[j])
            identity = "lake:" + min(children[j].address.key for j in group)
            lake_shapes, area, shore = _new_lake_geometry(base, patch, group, identity)
            if area < base.settings.min_lake_area_m2:
                continue
            connection = _route_channel(
                base,
                patch,
                source,
                "spill:" + identity,
                receivers,
                (*parent.footprints, *footprints),
                spill=True,
                spill_start=shore,
            )
            if connection is None:
                continue
            footprints.extend(lake_shapes)
            positions = []
            for j in group:
                positions.append(
                    _world_position(
                        base, flow_port(base, children[j].address, 0.5, 0.5, 0.0, 0.0).position
                    )
                )
                wet[j] = True
            visible = connection.area_m2 >= base.settings.min_river_area_m2
            target = connection.feature_id if visible else connection.downstream_ids[0]
            features.append(
                RefinedFeature(
                    identity,
                    "lake",
                    tuple(children[j].address.key for j in group),
                    tuple(positions),
                    (target,),
                    tuple(float(patch.surfaces_m[j]) for j in group),
                    float(area),
                    0.0,
                    parent.address.key,
                    connection.geometry,
                    connection.surface_m,
                    connection.feature_id if visible else None,
                )
            )
            if visible:
                features.append(connection)
        elif (
            not wet[i]
            and patch.imported_accumulation_m2[i] == 0
            and patch.accumulation_m2[i] >= base.settings.min_river_area_m2
        ):
            feature = _route_channel(
                base,
                patch,
                i,
                "river:" + children[i].address.key,
                receivers,
                (*parent.footprints, *footprints),
            )
            if feature is not None:
                features.append(feature)
    return tuple(sorted(features, key=lambda f: f.feature_id)), tuple(footprints)


@dataclass(frozen=True)
class CellState:
    address: CellAddress
    model_id: str
    local_area_m2: float
    incoming: tuple[FlowPort, ...]
    outlet: FlowPort
    surface_m: float
    destination_id: str
    anchor: WaterFeature | None = None
    inherited: tuple[WaterFeature, ...] = ()
    footprints: tuple[WaterFootprint, ...] = ()

    @property
    def total_area_m2(self) -> float:
        return self.local_area_m2 + math.fsum(port.area_m2 for port in self.incoming)


def _point(base: WorldBackbone, face: str, u: float, v: float) -> tuple[str, tuple]:
    un, ud = u.as_integer_ratio()
    vn, vd = v.as_integer_ratio()
    denominator = max(ud, vd)
    un, vn = un * (denominator // ud), vn * (denominator // vd)
    cols, rows = base.mesh.layout.columns, base.mesh.layout.rows
    if base.world.geometry == "sphere":
        normal, right, down = FACES[face]
        key = tuple(
            normal[i] * cols * denominator
            + right[i] * (2 * un - cols * denominator)
            + down[i] * (2 * vn - rows * denominator)
            for i in range(3)
        )
        divisor = math.gcd(*key)
        key = tuple(value // divisor for value in key)
        length = math.hypot(*key)
        point = tuple(value / length for value in key)
        return "sphere:" + ":".join(map(str, key)), point
    if base.world.boundary == "wrap_x":
        un %= cols * denominator
    divisor = math.gcd(un, vn, denominator)
    key = un // divisor, vn // divisor, denominator // divisor
    point = (
        un / (denominator * cols) * base.world.width_m,
        vn / (denominator * rows) * base.world.height_m,
        0.0,
    )
    return "flat:" + ":".join(map(str, key)), point


def _native(base: WorldBackbone, address: CellAddress, port: FlowPort) -> tuple[float, float]:
    values = tuple(int(value) for value in port.port_id.split(":")[1:])
    if base.world.geometry == "sphere":
        normal, right, down = FACES[address.face]
        denominator = sum(a * b for a, b in zip(values, normal, strict=True))
        if denominator <= 0:
            raise ValueError("port does not lie on this cell face")
        u = base.mesh.layout.columns * Fraction(
            denominator + sum(a * b for a, b in zip(values, right, strict=True)), 2 * denominator
        )
        v = base.mesh.layout.rows * Fraction(
            denominator + sum(a * b for a, b in zip(values, down, strict=True)), 2 * denominator
        )
        return float(u), float(v)
    u, v = values[0] / values[2], values[1] / values[2]
    if base.world.boundary == "wrap_x" and u < address.bounds[0]:
        u += base.mesh.layout.columns
    return u, v


def flow_port(
    base: WorldBackbone, address: CellAddress, u: float, v: float, surface_m: float, area_m2: float
) -> FlowPort:
    """Give one physical point the same identity across levels, cube seams and wrapped edges."""
    for value, name in ((u, "u"), (v, "v"), (surface_m, "surface_m"), (area_m2, "area_m2")):
        finite(value, name)
    if not 0 <= u <= 1 or not 0 <= v <= 1 or area_m2 < 0:
        raise ValueError("port must lie in the parent cell and have non-negative flux")
    x0, y0, x1, y1 = address.bounds
    identity, point = _point(base, address.face, x0 + u * (x1 - x0), y0 + v * (y1 - y0))
    return FlowPort(identity, point, float(surface_m), float(area_m2))


def _coarse_lake_outlets(base: WorldBackbone) -> tuple[dict, tuple]:
    """Materialize existing coarse lake handoffs without mutating the saved backbone."""
    mesh, d = base.mesh, base.drainage
    lake_records = {f.feature_id: f for f in base.features if f.kind == "lake"}
    targets = {f.nodes[0]: f for f in base.features if f.kind not in ("sea", "lake")}
    details, spills = {}, []
    for group in d.lake_groups:
        first = min(group, key=lambda i: d.rank[i])
        downstream = int(d.targets[first])
        if downstream < 0:
            continue
        identity = "lake:" + mesh.cell_ids[group[0]]
        old = lake_records[identity]
        vertex = int(d.outlet_ports[first])
        points = (mesh.positions[first], mesh.vertex_positions[vertex], mesh.positions[downstream])
        nodes = (mesh.cell_ids[first], mesh.vertex_ids[vertex], mesh.cell_ids[downstream])
        levels = (
            float(d.surface_m[first]),
            float((d.surface_m[first] + d.surface_m[downstream]) / 2),
            float(d.surface_m[downstream]),
        )
        geometry = tuple(_world_position(base, p) for p in points)
        recipient = targets.get(mesh.cell_ids[downstream])
        if recipient is not None and recipient.kind == "world-outlet":
            geometry += recipient.geometry[1:]
            nodes += recipient.nodes[1:]
            levels += recipient.surface_m[1:]
        _, _, face, level, x, y = mesh.cell_ids[first].split(":")
        owner = CellAddress(face, int(level), int(x), int(y)).key
        area = float(d.accumulation_m2[first])
        visible = area >= base.settings.min_river_area_m2
        outlet_id = "spill:" + identity if visible else None
        if visible:
            spills.append(
                RefinedFeature(
                    outlet_id,
                    "river",
                    nodes,
                    geometry,
                    old.downstream_ids,
                    levels,
                    area,
                    min(base.settings.max_channel_width_m, max(1.0, math.sqrt(area / 1_000_000))),
                    owner,
                )
            )
        details[identity] = RefinedFeature(
            old.feature_id,
            old.kind,
            old.nodes,
            old.geometry,
            old.downstream_ids,
            old.surface_m,
            old.area_m2,
            old.width_m,
            owner,
            geometry,
            levels,
            outlet_id,
        )
    return details, tuple(spills)


def _vertex_count(feature: WaterFeature) -> int:
    return len(feature.geometry) + len(getattr(feature, "outlet_geometry", ()))


def root_cells(base: WorldBackbone) -> tuple[CellState, ...]:
    """Import only already solved backbone fluxes; never evaluate upstream fine patches."""
    mesh, drainage = base.mesh, base.drainage
    details, spills = _coarse_lake_outlets(base)
    owners = {}
    cell_ids = set(mesh.cell_ids)
    spills_at = {}
    for spill in spills:
        for node in spill.nodes:
            if node in cell_ids:
                spills_at.setdefault(node, []).append(spill)
    for feature in base.features:
        members = feature.nodes if feature.kind in ("sea", "lake") else feature.nodes[:1]
        for node in members:
            if node in cell_ids:
                owners[node] = details.get(feature.feature_id, feature)
    destinations = {}
    for i in np.argsort(drainage.rank):
        destinations[i] = owners.get(mesh.cell_ids[i]) or destinations[drainage.targets[i]]
    addresses = tuple(
        CellAddress(*((parts := key.split(":"))[2], int(parts[3]), int(parts[4]), int(parts[5])))
        for key in mesh.cell_ids
    )
    footprints = _root_footprints(base)
    outlets = []
    for i, address in enumerate(addresses):
        parent, vertex = drainage.targets[i], drainage.outlet_ports[i]
        if vertex >= 0:
            edge = int(np.flatnonzero(mesh.edge_vertices[i] == vertex)[0])
            u, v = ((0.5, 0.0), (1.0, 0.5), (0.5, 1.0), (0.0, 0.5))[edge]
        else:
            u = v = 0.5
        surface = (
            (drainage.surface_m[i] + drainage.surface_m[parent]) / 2
            if parent >= 0
            else drainage.surface_m[i]
        )
        local_shapes = footprints[i] + (footprints[parent] if parent >= 0 else ())
        actual = _surface_profile(base, address, (u, v), local_shapes)
        if actual is not None:
            surface = actual
        outlets.append(
            flow_port(base, address, u, v, float(surface), float(drainage.accumulation_m2[i]))
        )
    incoming = [[] for _ in addresses]
    for i, parent in enumerate(drainage.targets):
        if parent >= 0:
            incoming[parent].append(outlets[i])
    result = []
    identity = base.model_id
    for i, address in enumerate(addresses):
        owner = owners.get(mesh.cell_ids[i])
        inherited = {
            feature.feature_id: feature
            for j in (i, *mesh.neighbours[i])
            if (feature := owners.get(mesh.cell_ids[j])) is not None
        }
        for spill in spills_at.get(mesh.cell_ids[i], ()):
            inherited[spill.feature_id] = spill
        result.append(
            CellState(
                address,
                identity,
                float(mesh.areas_m2[i]),
                tuple(sorted(incoming[i], key=lambda p: p.port_id)),
                outlets[i],
                float(drainage.surface_m[i]),
                destinations[i].feature_id,
                owner if owner is not None and owner.kind == "river" else None,
                tuple(inherited[key] for key in sorted(inherited)),
                footprints[i],
            )
        )
    count = sum(len(p.vertices) for row in footprints for p in row)
    count += sum(_vertex_count(details.get(f.feature_id, f)) for f in base.features)
    count += sum(_vertex_count(f) for f in spills)
    if count > LIMITS["geometry_vertices"]:
        raise ValueError("inherited water geometry exceeds vertex budget")
    return tuple(result)


@dataclass(frozen=True)
class RefinementPatch:
    parent: CellState
    children: tuple[CellState, ...]
    local_areas_m2: NDArray[np.float64]
    injected_m2: NDArray[np.float64]
    targets: NDArray[np.int64]
    rank: NDArray[np.int64]
    accumulation_m2: NDArray[np.float64]
    imported_accumulation_m2: NDArray[np.float64]
    surfaces_m: NDArray[np.float64]
    ground_m: NDArray[np.float64]
    features: tuple[WaterFeature, ...] = ()
    footprints: tuple[WaterFootprint, ...] = ()

    def to_dict(self) -> dict:
        return {
            "parent": self.parent.address.key,
            "model_id": self.parent.model_id,
            "children": [asdict(child) for child in self.children],
            **{
                name: getattr(self, name).tolist()
                for name in (
                    "local_areas_m2",
                    "injected_m2",
                    "targets",
                    "rank",
                    "accumulation_m2",
                    "imported_accumulation_m2",
                    "surfaces_m",
                    "ground_m",
                )
            },
            "features": [asdict(feature) for feature in self.features],
            "footprints": [asdict(p) for p in self.footprints],
        }


def _children_geometry(
    base: WorldBackbone, parent: CellState
) -> tuple[tuple[CellAddress, ...], NDArray]:
    p = parent.address
    addresses = tuple(
        CellAddress(p.face, p.level + 1, p.x * 4 + x, p.y * 4 + y)
        for y in range(4)
        for x in range(4)
    )
    areas = []
    for address in addresses:
        x0, y0, x1, y1 = address.bounds
        if base.world.geometry == "flat":
            areas.append(
                (x1 - x0)
                * base.world.width_m
                / base.mesh.layout.columns
                * (y1 - y0)
                * base.world.height_m
                / base.mesh.layout.rows
            )
            continue
        a, b, c, d = [
            np.asarray(_point(base, p.face, float(x), float(y))[1])
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        ]
        area = 0.0
        triangle_points = ((a, b, c), (a, c, d))
        for a, b, c in triangle_points:
            if base.world.geometry == "sphere":
                area += (
                    2
                    * math.atan2(
                        abs(float(np.dot(a, np.cross(b, c)))),
                        1 + float(np.dot(a, b) + np.dot(b, c) + np.dot(c, a)),
                    )
                    * base.world.radius_m**2
                )
            else:
                area += abs(float(np.cross(b - a, c - a)[2])) / 2
        areas.append(area)
    areas = np.asarray(areas)
    if not np.isfinite(areas).all() or (areas <= 0).any():
        raise ValueError("refined cell geometry exceeds numerical precision")
    areas *= parent.local_area_m2 / math.fsum(areas)
    areas[-1] = parent.local_area_m2 - math.fsum(areas[:-1])
    return addresses, areas


def _owner(base: WorldBackbone, parent: CellState, port: FlowPort) -> int:
    u, v = _native(base, parent.address, port)
    x0, y0, x1, y1 = parent.address.bounds
    u, v = (u - x0) / (x1 - x0), (v - y0) / (y1 - y0)
    if not -1e-10 <= u <= 1 + 1e-10 or not -1e-10 <= v <= 1 + 1e-10:
        raise ValueError("inherited port lies outside its parent")
    return min(3, max(0, math.floor(4 * v))) * 4 + min(3, max(0, math.floor(4 * u)))


def _neighbours(i: int) -> tuple[int, ...]:
    x, y = i % 4, i // 4
    return tuple(
        j
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))
        if 0 <= x + dx < 4 and 0 <= y + dy < 4
        for j in ((y + dy) * 4 + x + dx,)
    )


def _validate_parent(base: WorldBackbone, parent: CellState) -> None:
    address = parent.address
    if parent.model_id != base.model_id:
        raise ValueError("cell belongs to another hydrology model")
    if address.level >= base.mesh.layout.depth:
        raise ValueError("cell is already at the saved finest scale")
    if (base.world.geometry == "flat") != (address.face == "flat"):
        raise ValueError("cell face is incompatible with world geometry")
    if (
        address.x >= base.mesh.layout.columns * 4**address.level
        or address.y >= base.mesh.layout.rows * 4**address.level
    ):
        raise ValueError("cell address lies outside the world")
    finite(parent.local_area_m2, "local source area")
    if parent.local_area_m2 <= 0:
        raise ValueError("local source area must be positive")
    for port in (*parent.incoming, parent.outlet):
        finite(port.area_m2, "port area")
        finite(port.surface_m, "port surface")
        if port.area_m2 < 0:
            raise ValueError("port area must be non-negative")
    finite(parent.surface_m, "parent surface")


def _routing_constraints(base: WorldBackbone, parent: CellState, raw: NDArray) -> tuple:
    root = _owner(base, parent, parent.outlet)
    priorities = step_rng(
        base.world.seed, "world.water.refinement:" + parent.address.key
    ).permutation(16)
    forced, locked, caps, edges = _forced_routes(base, parent, root)
    for port in parent.incoming:
        i = _owner(base, parent, port)
        caps[i] = min(caps.get(i, math.inf), port.surface_m)
    caps[root] = parent.outlet.surface_m
    u, v = _native(base, parent.address, parent.outlet)
    x0, y0, x1, y1 = parent.address.bounds
    outlet_uv = ((u - x0) / (x1 - x0), (v - y0) / (y1 - y0))
    _complete_inlets(
        forced, locked, caps, raw, root, priorities, parent.outlet.surface_m, edges, outlet_uv
    )
    return root, priorities, forced, locked, caps, edges


def refine_patch(base: WorldBackbone, parent: CellState, ground_m: NDArray) -> RefinementPatch:
    """Solve sixteen child budgets toward one prescribed outlet, independently of query bounds."""
    _validate_parent(base, parent)
    raw = np.asarray(ground_m)
    if raw.dtype.kind not in "fiu" or raw.shape != (16,) or not np.isfinite(raw).all():
        raise ValueError("ground must contain sixteen finite real elevations")
    if not math.isclose(parent.total_area_m2, parent.outlet.area_m2, rel_tol=1e-12):
        raise ValueError("inherited outlet does not conserve local and imported source area")
    addresses, areas = _children_geometry(base, parent)
    incoming = [[] for _ in addresses]
    injected = np.zeros(16)
    for port in parent.incoming:
        i = _owner(base, parent, port)
        incoming[i].append(port)
        injected[i] += port.area_m2
    root, priorities, forced, locked, caps, edges = _routing_constraints(base, parent, raw)
    surfaces = raw.astype(float, copy=True)
    surfaces[root] = parent.outlet.surface_m
    targets, visited, order = np.full(16, -1, dtype=np.int64), {root}, []
    queue = [(float(surfaces[root]), int(priorities[root]), root)]
    while queue:
        level, _, i = heapq.heappop(queue)
        order.append(i)
        for j in _neighbours(i):
            if j in visited or (j in forced and forced[j] != i):
                continue
            boundary = locked[j][1] if j in locked else edges.get((j, i))
            if boundary is not None and (
                boundary + 1e-9 < level or boundary > caps.get(j, math.inf) + 1e-9
            ):
                continue
            visited.add(j)
            targets[j] = i
            surfaces[j] = (
                locked[j][1]
                if j in locked
                else max(
                    level,
                    boundary if boundary is not None else -math.inf,
                    min(float(surfaces[j]), caps.get(j, math.inf)),
                )
            )
            if surfaces[j] + 1e-9 < level:
                raise ValueError("inherited water profile rises downstream")
            heapq.heappush(queue, (float(surfaces[j]), int(priorities[j]), j))
    if len(order) != 16:
        raise ValueError("inherited channel constraints disconnect the canonical patch")
    rank = np.empty(16, dtype=np.int64)
    rank[order] = np.arange(16)
    accumulation, imported = areas + injected, injected.copy()
    for i in reversed(order):
        j = targets[i]
        if j >= 0:
            accumulation[j] += accumulation[i]
            imported[j] += imported[i]
    groups = _lake_groups(base, parent, addresses, areas, raw, surfaces, imported)
    lake_at = {i: group for group in groups for i in group}
    for group in groups:
        first = min(group, key=lambda i: rank[i])
        members, seen, queue = set(group), {first}, [first]
        for i in queue:
            for j in _neighbours(i):
                if j in members and j not in seen:
                    seen.add(j)
                    targets[j] = i
                    queue.append(j)
    adjacency = [[] for _ in range(16)]
    for i, j in enumerate(targets):
        if j >= 0:
            adjacency[j].append(i)
    order = [root]
    for i in order:
        order.extend(adjacency[i])
    if len(order) != 16:
        raise ValueError("constrained lake routing contains a cycle")
    rank[order] = np.arange(16)
    accumulation, imported = areas + injected, injected.copy()
    for i in reversed(order):
        j = targets[i]
        if j >= 0:
            accumulation[j] += accumulation[i]
            imported[j] += imported[i]
    outlets = []
    for i, address in enumerate(addresses):
        j = targets[i]
        if j < 0:
            port = parent.outlet
        else:
            if i in locked:
                uv, level = locked[i]
                u, v = uv[0] * 4 - i % 4, uv[1] * 4 - i // 4
            else:
                dx, dy = int(j % 4 - i % 4), int(j // 4 - i // 4)
                u, v = 0.5 + 0.5 * dx, 0.5 + 0.5 * dy
                level = float(edges.get((i, int(j)), (surfaces[i] + surfaces[j]) / 2))
                if i in lake_at and j not in lake_at[i]:
                    level = float(surfaces[i])
            port = flow_port(base, address, float(u), float(v), level, float(accumulation[i]))
            incoming[j].append(port)
        outlets.append(port)
    children = tuple(
        CellState(
            address,
            parent.model_id,
            float(areas[i]),
            tuple(sorted(incoming[i], key=lambda p: p.port_id)),
            outlets[i],
            float(surfaces[i]),
            parent.destination_id,
            None,
            parent.inherited,
        )
        for i, address in enumerate(addresses)
    )
    patch = RefinementPatch(
        parent,
        children,
        areas,
        injected,
        targets,
        rank,
        accumulation,
        imported,
        surfaces,
        raw.astype(float, copy=True),
    )

    features, footprints = _local_features(base, patch)
    all_features = {f.feature_id: f for f in (*parent.inherited, *features)}
    children = []
    for child in patch.children:
        own = next(
            (
                f
                for f in features
                if f.kind == "river" and f.feature_id == "river:" + child.address.key
            ),
            None,
        )
        inherited = tuple(
            f
            for f in (all_features[key] for key in sorted(all_features))
            if f.kind != "river" or _intersects(base, child.address, f)
        )
        shapes = tuple(
            p
            for p in (*parent.footprints, *footprints)
            if _footprint_intersects(base, child.address, p)
        )
        children.append(
            replace(
                child,
                anchor=own,
                inherited=inherited,
                footprints=shapes,
                destination_id=own.feature_id if own is not None else parent.destination_id,
            )
        )
    count = sum(_vertex_count(f) for f in features) + sum(len(p.vertices) for p in footprints)
    if count > LIMITS["geometry_vertices"]:
        raise ValueError("refinement geometry exceeds vertex budget")
    return replace(patch, children=tuple(children), features=features, footprints=footprints)


def refine_cell(base: WorldBackbone, parent: CellState) -> RefinementPatch:
    """Sample coordinate-keyed terrain for one canonical patch; no neighbouring fine work."""
    from pixel_world.regional import terrain_samples

    _validate_parent(base, parent)
    addresses, _ = _children_geometry(base, parent)
    points = np.asarray([flow_port(base, a, 0.5, 0.5, 0.0, 0.0).position for a in addresses])
    if base.world.geometry == "sphere":
        x, y, z = points.T
        first = np.rad2deg(np.arctan2(y, x))
        second = np.rad2deg(np.arctan2(z, np.hypot(x, y)))
    else:
        first, second = points[:, 0], points[:, 1]
    ground = base.world.height_min_m + terrain_samples(base.world, first, second) * (
        base.world.height_range_m / 65535
    )
    return refine_patch(base, parent, ground)


@dataclass(frozen=True, order=True)
class WaterWindow:
    face: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        if self.face not in ("flat", *FACES):
            raise ValueError("unknown water window face")
        for name in ("x_min", "y_min", "x_max", "y_max"):
            finite(getattr(self, name), name)
        if self.x_min >= self.x_max or self.y_min >= self.y_max:
            raise ValueError("water window must have positive extent")


def _sphere_context(
    base: WorldBackbone, window: WaterWindow, padding: float
) -> tuple[WaterWindow, ...]:
    n = base.mesh.layout.columns
    if padding >= n / 2:
        return tuple(WaterWindow(face, 0.0, 0.0, float(n), float(n)) for face in sorted(FACES))
    normal, right, down = map(np.asarray, FACES[window.face])
    u0, u1 = 2 * (window.x_min - padding) / n - 1, 2 * (window.x_max + padding) / n - 1
    v0, v1 = 2 * (window.y_min - padding) / n - 1, 2 * (window.y_max + padding) / n - 1
    planes = (
        right - u0 * normal,
        u1 * normal - right,
        down - v0 * normal,
        v1 * normal - down,
        normal,
    )
    result = []
    for face in sorted(FACES):
        target, east, south = map(np.asarray, FACES[face])
        polygon = [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)]
        for plane in planes:
            clipped = []
            for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True):
                fa = float(np.dot(plane, target + a[0] * east + a[1] * south))
                fb = float(np.dot(plane, target + b[0] * east + b[1] * south))
                if (fa >= 0) != (fb >= 0):
                    t = fa / (fa - fb)
                    clipped.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
                if fb >= 0:
                    clipped.append(b)
            polygon = clipped
            if not polygon:
                break
        if len(polygon) < 3:
            continue
        x0, x1 = (
            max(0.0, (min(x for x, y in polygon) + 1) * n / 2),
            min(float(n), (max(x for x, y in polygon) + 1) * n / 2),
        )
        y0, y1 = (
            max(0.0, (min(y for x, y in polygon) + 1) * n / 2),
            min(float(n), (max(y for x, y in polygon) + 1) * n / 2),
        )
        if x0 < x1 and y0 < y1:
            result.append(WaterWindow(face, x0, y0, x1, y1))
    return tuple(result)


def _working_windows(
    base: WorldBackbone, windows: tuple[WaterWindow, ...]
) -> tuple[WaterWindow, ...]:
    if not windows or len(windows) > LIMITS["refinement_windows"]:
        raise ValueError("water window count exceeds request budget")
    cols, rows = base.mesh.layout.columns, base.mesh.layout.rows
    result = []
    for window in windows:
        if not isinstance(window, WaterWindow):
            raise ValueError("water query requires WaterWindow values")
        if window.y_min < 0 or window.y_max > rows:
            raise ValueError("water window lies outside the world")
        if base.world.geometry == "sphere":
            if window.face == "flat" or window.x_min < 0 or window.x_max > cols:
                raise ValueError("invalid spherical water window")
            padding = 128 * 3 * math.sqrt(3) * cols / (2 * base.world.radius_m)
            result.extend(_sphere_context(base, window, padding))
        else:
            if window.face != "flat" or window.x_max - window.x_min > cols:
                raise ValueError("invalid flat water window")
            dx, dy = 128 * cols / base.world.width_m, 128 * rows / base.world.height_m
            y0, y1 = max(0.0, window.y_min - dy), min(float(rows), window.y_max + dy)
            if base.world.boundary == "bounded":
                if window.x_min < 0 or window.x_max > cols:
                    raise ValueError("water window lies outside the bounded world")
                result.append(
                    WaterWindow(
                        "flat",
                        max(0.0, window.x_min - dx),
                        y0,
                        min(float(cols), window.x_max + dx),
                        y1,
                    )
                )
            elif window.x_max - window.x_min + 2 * dx >= cols:
                result.append(WaterWindow("flat", 0.0, y0, float(cols), y1))
            else:
                x0 = (window.x_min - dx) % cols
                x1 = x0 + (window.x_max - window.x_min) + 2 * dx
                result.append(WaterWindow("flat", x0, y0, min(float(cols), x1), y1))
                if x1 > cols:
                    result.append(WaterWindow("flat", 0.0, y0, x1 - cols, y1))
    return tuple(sorted(set(result)))


def _union_count(rectangles: list[tuple[int, int, int, int]]) -> int:
    count = 0
    edges = sorted({x for x0, y0, x1, y1 in rectangles for x in (x0, x1)})
    for left, right in zip(edges[:-1], edges[1:], strict=True):
        intervals = sorted((y0, y1) for x0, y0, x1, y1 in rectangles if x0 <= left < x1)
        covered, last = 0, -1
        for a, b in intervals:
            covered += max(0, b - max(a, last))
            last = max(last, b)
        count += (right - left) * covered
    return count


def _work_count(base: WorldBackbone, windows: tuple[WaterWindow, ...]) -> int:
    count = 0
    if base.mesh.layout.depth > base.settings.max_refinement_depth:
        raise ValueError("refinement depth exceeds saved limit")
    for level in range(base.mesh.layout.depth):
        scale = 4**level
        for face in sorted({window.face for window in windows}):
            rectangles = [
                (
                    math.floor(w.x_min * scale),
                    math.floor(w.y_min * scale),
                    math.ceil(w.x_max * scale),
                    math.ceil(w.y_max * scale),
                )
                for w in windows
                if w.face == face
            ]
            count += _union_count(rectangles)
            if count > LIMITS["refinement_patches"]:
                raise ValueError("refinement patch budget exceeded; request a smaller area")
    return count


def _touches(address: CellAddress, windows: tuple[WaterWindow, ...]) -> bool:
    x0, y0, x1, y1 = address.bounds
    return any(
        w.face == address.face and x0 < w.x_max and x1 > w.x_min and y0 < w.y_max and y1 > w.y_min
        for w in windows
    )


@dataclass(frozen=True)
class RefinedWater:
    world: WorldDefinition
    settings: HydrologyDefinition
    model_id: str
    finest_cell_span_m: float
    windows: tuple[WaterWindow, ...]
    features: tuple[WaterFeature, ...]
    footprints: tuple[WaterFootprint, ...]
    patches_evaluated: int
    max_live_patches: int
    cache_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "format": "internal-refinement-v1",
            "seed": self.world.seed,
            "generator_version": self.world.generator_version,
            "world": self.world.to_dict(),
            "parameters": self.settings.to_dict(),
            "model_id": self.model_id,
            "finest_cell_span_m": self.finest_cell_span_m,
            "exact_global_drainage": False,
            "windows": [asdict(w) for w in self.windows],
            "features": [asdict(f) for f in self.features],
            "footprints": [asdict(p) for p in self.footprints],
        }


def query_water(base: WorldBackbone, windows: tuple[WaterWindow, ...]) -> RefinedWater:
    """Stream only intersecting canonical patches and a fixed bank context; retain no fine cache."""
    working = _working_windows(base, windows)
    expected = _work_count(base, working)
    features, footprints = {}, {}
    vertices = evaluated = peak = 0

    def collect(feature_values: tuple, shape_values: tuple) -> None:
        nonlocal vertices
        for feature in feature_values:
            if feature.feature_id not in features:
                vertices += _vertex_count(feature)
                features[feature.feature_id] = feature
        for shape in shape_values:
            key = (shape.feature_id, shape.parent_id, shape.vertices)
            if key not in footprints:
                vertices += len(shape.vertices)
                footprints[key] = shape
        if vertices > LIMITS["geometry_vertices"]:
            raise ValueError("query water geometry exceeds vertex budget; request a smaller area")

    def visit(parent: CellState) -> None:
        nonlocal evaluated, peak
        if parent.address.level >= base.mesh.layout.depth:
            return
        patch = refine_cell(base, parent)
        evaluated += 1
        peak = max(peak, parent.address.level + 1)
        collect(patch.features, patch.footprints)
        for child in patch.children:
            if _touches(child.address, working):
                visit(child)

    for parent in root_cells(base):
        if _touches(parent.address, working):
            collect(parent.inherited, parent.footprints)
            visit(parent)
    if evaluated != expected:
        raise ValueError("canonical refinement work does not match preflight")
    return RefinedWater(
        world=base.world,
        settings=base.settings,
        model_id=base.model_id,
        finest_cell_span_m=base.settings.finest_cell_span_m,
        windows=tuple(sorted(set(windows))),
        features=tuple(features[key] for key in sorted(features)),
        footprints=tuple(footprints[key] for key in sorted(footprints)),
        patches_evaluated=evaluated,
        max_live_patches=peak,
    )
