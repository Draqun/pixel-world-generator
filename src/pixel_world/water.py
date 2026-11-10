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
