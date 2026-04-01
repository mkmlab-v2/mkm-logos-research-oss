# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.25, L:0.25, K:0.25, M:0.25}
# Balance: 78
# Purpose: Bipartite max-sum cosine assignment between 16 Myeongni state 4D and 16 ranked verse 4D.
# Keywords: logos, myeongni, assignment, cosine, B-track
"""Assign each of 16 Myeongni state fingerprints to exactly one Logos verse (4D cosine).

Inputs:
  - Ranked verses: JSON from refine_top_1_percent_logos.py (16 hits, any score field).
  - State vectors: data/myeongni/16_STATE_MASTER_PROBE_v1.json → states[].vector_4d, state_id 1..16.
  - Verse vectors: data/logos/verse_4pipeline_full_31102.json → pipeline4_unified_v2.vector_4d.

Uses scipy linear_sum_assignment to **maximize** sum of cosines (cost = negative cosine).

B-track / research only. Not a trading signal. Do not merge into A-track OOF without explicit SSOT.

Default output: docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json (tracked snapshot).
Re-run after changing ranked TOP16 or probe vectors; CI does not recompute this unless a workflow step is added.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))
from tools.myeongni.manseryeok_provenance import logos_myeongni_state_join_scope

try:
    from scipy.optimize import linear_sum_assignment
except ImportError as e:  # pragma: no cover
    raise SystemExit("scipy required: pip install scipy") from e


_AXES: Sequence[str] = ("S", "L", "K", "M")


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _vec_from_dict(d: Mapping[str, Any]) -> np.ndarray:
    return np.array([float(d[k]) for k in _AXES], dtype=np.float64)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _load_verse_index(pipeline_path: Path) -> Dict[str, Dict[str, float]]:
    data = json.loads(pipeline_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Expected verse JSON as a list of rows")
    out: Dict[str, Dict[str, float]] = {}
    for row in data:
        vid = row.get("verse_id")
        p4 = row.get("pipeline4_unified_v2") or {}
        v4 = p4.get("vector_4d") if isinstance(p4, dict) else None
        if not vid or not isinstance(v4, dict):
            continue
        out[str(vid).strip()] = {k: float(v4[k]) for k in _AXES}
    return out


def _load_states(probe_path: Path) -> List[Tuple[int, np.ndarray]]:
    doc = json.loads(probe_path.read_text(encoding="utf-8"))
    states = doc.get("states") or []
    rows: List[Tuple[int, np.ndarray]] = []
    for s in states:
        sid = int(s["state_id"])
        v = _vec_from_dict(s["vector_4d"])
        rows.append((sid, v))
    rows.sort(key=lambda x: x[0])
    if len(rows) != 16 or [r[0] for r in rows] != list(range(1, 17)):
        raise ValueError("Expected 16 states with state_id 1..16")
    return rows


def run_assignment(
    *,
    ranked_path: Path,
    probe_path: Path,
    pipeline_path: Path,
    output_path: Path,
) -> Dict[str, Any]:
    ranked = json.loads(ranked_path.read_text(encoding="utf-8"))
    hits = ranked.get("hits") or []
    verse_ids = [str(h["verse_id"]).strip() for h in hits]
    if len(verse_ids) != 16:
        raise ValueError(f"Expected exactly 16 ranked hits, got {len(verse_ids)}")

    states = _load_states(probe_path)
    vix = _load_verse_index(pipeline_path)

    missing = [v for v in verse_ids if v not in vix]
    if missing:
        raise FileNotFoundError(f"verse_id not in pipeline file: {missing[:5]} ...")

    state_vecs = [v for _, v in states]
    verse_vecs = [_vec_from_dict(vix[vid]) for vid in verse_ids]

    n = 16
    cost = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(n):
            cost[i, j] = -cosine_sim(state_vecs[i], verse_vecs[j])

    row_ind, col_ind = linear_sum_assignment(cost)
    total_cos = 0.0
    assignments: List[Dict[str, Any]] = []
    for r, c in zip(row_ind, col_ind):
        sid = states[r][0]
        vid = verse_ids[c]
        cos = cosine_sim(state_vecs[r], verse_vecs[c])
        total_cos += cos
        assignments.append(
            {
                "state_id": sid,
                "verse_id": vid,
                "cosine_state_verse": cos,
            }
        )
    assignments.sort(key=lambda x: x["state_id"])

    out: Dict[str, Any] = {
        "schema": "logos_myeongni_state_join_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "max_sum_cosine_assignment_scipy_linear_sum_assignment",
        "disclaimer": "B-track research; not trading SSOT; not semantic destiny mapping.",
        "manseryeok_scope": logos_myeongni_state_join_scope(),
        "sources": {
            "ranked_json": str(ranked_path.resolve()),
            "probe_json": str(probe_path.resolve()),
            "verse_pipeline_json": str(pipeline_path.resolve()),
        },
        "rank_field_used": ranked.get("score_field"),
        "assignments": assignments,
        "total_cosine_sum": total_cos,
        "mean_cosine_per_pair": total_cos / n,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out["_output_path"] = str(output_path.resolve())
    return out


def _parse_args() -> argparse.Namespace:
    root = _workspace_root()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--ranked-json",
        type=Path,
        default=root
        / "backtest_results"
        / "sweep_kmin_refine"
        / "LOGOS_RESONANCE_BTC_EXT_ABSOLUTE_TOP16.json",
        help="Output of refine_top_1_percent_logos.py (16 hits)",
    )
    p.add_argument(
        "--probe",
        type=Path,
        default=root / "data" / "myeongni" / "16_STATE_MASTER_PROBE_v1.json",
    )
    p.add_argument(
        "--verse-pipeline",
        type=Path,
        default=root / "data" / "logos" / "verse_4pipeline_full_31102.json",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=root
        / "docs"
        / "final"
        / "artifacts"
        / "LOGOS_STATE_MAPPING_V1.json",
        help="Tracked artifact path under docs/final/artifacts/ (override if needed)",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    doc = run_assignment(
        ranked_path=args.ranked_json,
        probe_path=args.probe,
        pipeline_path=args.verse_pipeline,
        output_path=args.output,
    )
    path = doc.pop("_output_path", "")
    tsum = doc["total_cosine_sum"]
    mmean = doc["mean_cosine_per_pair"]
    print(
        f"LOGOS_STATE_JOIN: total_cosine_sum={tsum:.12f} mean_cosine_per_pair={mmean:.12f}",
        flush=True,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output": path,
                "total_cosine_sum": tsum,
                "mean_cosine_per_pair": mmean,
                "state_1_verse": next(
                    (a["verse_id"] for a in doc["assignments"] if a["state_id"] == 1),
                    None,
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
