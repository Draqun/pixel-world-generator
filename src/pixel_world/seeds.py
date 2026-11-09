"""Independent random streams per generation step."""

import hashlib

import numpy as np


def step_rng(master_seed: int, step_name: str) -> np.random.Generator:
    """Random generator that depends only on the master seed and the step name."""
    key = int.from_bytes(hashlib.sha256(step_name.encode("utf-8")).digest()[:8], "big")
    return np.random.Generator(
        np.random.PCG64(np.random.SeedSequence(master_seed, spawn_key=(key,)))
    )
