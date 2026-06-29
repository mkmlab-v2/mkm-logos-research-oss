"""Tests for Logos Studio embedding router tier-2."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n)))
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n)))
    return dot / (na * nb) if na and nb else 0.0


def test_embedding_index_has_fifty_vectors() -> None:
    path = ROOT / "docs/final/artifacts/logos_studio_semantic_router_embedding_index_v1_latest.json"
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    assert doc.get("preset_count") == 50
    assert len(doc.get("vectors") or []) == 50
    assert int(doc.get("vector_dim") or 0) >= 64


def test_encode_query_script_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/encode_logos_studio_query_embedding_v1.py"), "--query", "nephilim giants"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[:300]
    doc = json.loads(proc.stdout)
    assert doc.get("ok") is True
    assert len(doc.get("vector") or []) >= 64


def test_embedding_paraphrase_routes_to_bigset() -> None:
    index_path = ROOT / "docs/final/artifacts/logos_studio_semantic_router_embedding_index_v1_latest.json"
    index = json.loads(index_path.read_text(encoding="utf-8-sig"))
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/encode_logos_studio_query_embedding_v1.py"),
            "--query",
            "타락한 천사가 인간과 결혼한 고대 신화 전통",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0
    qvec = json.loads(proc.stdout)["vector"]
    threshold = float(index.get("min_cosine_threshold") or 0.42)
    best_id = None
    best = -1.0
    for row in index.get("vectors") or []:
        score = _cosine(qvec, list(row["vector"]))
        if score > best:
            best = score
            best_id = row["preset_id"]
    assert best >= threshold
    assert str(best_id).startswith("bigset_topic_")
