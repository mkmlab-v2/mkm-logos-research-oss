"""Shared helpers for Logos candidate edge lanes (4D kNN · ANN-lite)."""
from __future__ import annotations

from typing import Any


def edge_similarity(row: dict[str, Any]) -> float:
    if row.get("similarity_ann_lite_cosine") is not None:
        return float(row["similarity_ann_lite_cosine"])
    if row.get("similarity_4d_cosine") is not None:
        return float(row["similarity_4d_cosine"])
    return float(row.get("weight") or 0.0)


def edge_lane_id(row: dict[str, Any]) -> str:
    basis = row.get("relation_basis") or []
    if isinstance(basis, list) and "ann_lite_cosine" in basis:
        return "ann_lite"
    if row.get("edge_type") == "semantic_ann_lite_knn":
        return "ann_lite"
    return "offline_4d_knn"


def undirected_pair_key(src: str, dst: str) -> tuple[str, str]:
    return tuple(sorted((str(src), str(dst))))


def survivor_pair_keys(survivors: list[dict[str, Any]]) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for row in survivors:
        src = str(row.get("src_node_id") or "")
        dst = str(row.get("dst_node_id") or "")
        if src and dst:
            out.add(undirected_pair_key(src, dst))
    return out
