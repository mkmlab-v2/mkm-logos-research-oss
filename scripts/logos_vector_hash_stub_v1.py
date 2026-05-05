"""Shared deterministic hash_stub_v1 vectors for Track B Logos ANN lite (non-semantic).

Vectors are SHA-expanded floats, L2-normalized — for plumbing tests only.
"""
from __future__ import annotations

import hashlib
import math
import struct

EMBEDDING_MODE = "hash_stub_v1"


def hash_stub_v1_embedding_floats(seed: str, dim: int) -> list[float]:
    """L2-normalized float vector deterministic from seed string."""
    out_f: list[float] = []
    counter = 0
    while len(out_f) < dim:
        block = hashlib.sha256(f"logos_stub_v1|{seed}|{counter}".encode()).digest()
        for off in range(0, 32, 4):
            if len(out_f) >= dim:
                break
            u = int.from_bytes(block[off : off + 4], "little") / 2**32
            out_f.append(u * 2.0 - 1.0)
        counter += 1
    out_f = out_f[:dim]
    s = math.sqrt(sum(x * x for x in out_f)) or 1.0
    return [x / s for x in out_f]


def hash_stub_v1_embedding_blob(seed: str, dim: int) -> bytes:
    floats = hash_stub_v1_embedding_floats(seed, dim)
    return struct.pack(f"<{dim}f", *floats)
