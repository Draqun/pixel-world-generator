"""Deterministic sea connectivity and depression drainage."""

import heapq
from collections import deque

import numpy as np
from numpy.typing import NDArray


def drainage(
    height: NDArray[np.uint16], sea_level: float, height_range_m: float, min_lake_depth_m: float
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.float64], NDArray[np.int64]]:
    """Return ocean mask, filled elevations in metres, and flattened downstream indices."""
    rows, cols = height.shape
    ground = height.astype(np.float64) * (height_range_m / 65535)
    datum = sea_level * height_range_m
    sea = np.zeros(height.shape, dtype=bool)

    def neighbours(index: int):
        y, x = divmod(index, cols)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if (dy or dx) and 0 <= ny < rows and 0 <= nx < cols:
                    yield ny * cols + nx

    boundary = [
        i for i in range(height.size) if i // cols in (0, rows - 1) or i % cols in (0, cols - 1)
    ]
    queue = deque(i for i in boundary if ground.flat[i] < datum)
    for i in queue:
        sea.flat[i] = True
    while queue:
        for j in neighbours(queue.popleft()):
            if not sea.flat[j] and ground.flat[j] < datum:
                sea.flat[j] = True
                queue.append(j)

    filled = ground.copy()
    filled[sea] = datum
    targets = np.full(height.shape, -1, dtype=np.int64)
    visited = sea.copy()
    heap = [(datum, int(i)) for i in np.flatnonzero(sea)]
    for i in boundary:
        if not visited.flat[i]:
            visited.flat[i] = True
            heap.append((float(filled.flat[i]), i))
    heapq.heapify(heap)
    while heap:
        level, i = heapq.heappop(heap)
        for j in neighbours(i):
            if not visited.flat[j]:
                visited.flat[j] = True
                filled.flat[j] = max(level, ground.flat[j])
                targets.flat[j] = i
                heapq.heappush(heap, (float(filled.flat[j]), j))
    lake = ~sea & (filled > ground) & ((filled - ground) >= min_lake_depth_m)
    return sea, lake, filled, targets


def accumulation(targets: NDArray[np.int64]) -> NDArray[np.int64]:
    """Count every upstream cell once, in topological order."""
    flat = targets.ravel()
    incoming = np.bincount(flat[flat >= 0], minlength=flat.size)
    area = np.ones(flat.size, dtype=np.int64)
    queue = np.empty(flat.size, dtype=np.int64)
    leaves = np.flatnonzero(incoming == 0)
    tail = len(leaves)
    queue[:tail] = leaves
    head = 0
    while head < tail:
        i = queue[head]
        head += 1
        target = flat[i]
        if target >= 0:
            area[target] += area[i]
            incoming[target] -= 1
            if incoming[target] == 0:
                queue[tail] = target
                tail += 1
    if tail != flat.size:
        raise ValueError("drainage targets contain a cycle")
    return area.reshape(targets.shape)


def rivers(
    area: NDArray[np.int64],
    sea: NDArray[np.bool_],
    lake: NDArray[np.bool_],
    threshold: int = 256,
    max_width: int = 9,
) -> tuple[NDArray[np.bool_], NDArray[np.uint8]]:
    """Return thresholded centrelines and widened categorical water."""
    centre = area >= threshold
    max_radius = (max_width - 1) // 2
    radius = np.zeros(area.shape, dtype=np.uint8)
    radius[centre] = np.minimum(
        np.floor(np.log2(area[centre] / threshold)).astype(np.int64), max_radius
    )
    river = centre.copy()
    rows, cols = area.shape
    for dy in range(-max_radius, max_radius + 1):
        for dx in range(-max_radius, max_radius + 1):
            distance = int(np.ceil(np.hypot(dy, dx)))
            if distance == 0 or distance > max_radius or abs(dy) >= rows or abs(dx) >= cols:
                continue
            src_y = slice(max(0, -dy), min(rows, rows - dy))
            src_x = slice(max(0, -dx), min(cols, cols - dx))
            dst_y = slice(max(0, dy), min(rows, rows + dy))
            dst_x = slice(max(0, dx), min(cols, cols + dx))
            river[dst_y, dst_x] |= centre[src_y, src_x] & (radius[src_y, src_x] >= distance)
    water = np.zeros(area.shape, dtype=np.uint8)
    water[river] = 3
    water[lake] = 2
    water[sea] = 1
    return centre, water
