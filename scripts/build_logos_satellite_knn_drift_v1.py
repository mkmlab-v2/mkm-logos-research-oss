#!/usr/bin/env python3
"""kNN-style L2 drift: satellite lane vs canonical medoid (B-track, no merge)."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CORPUS = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_single_anchor_v1_latest.jsonl"
DEFAULT_APOCRYPHA = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_apocrypha_lane_v1_latest.jsonl"
DEFAULT_MEDOIDS = ROOT / "docs/final/artifacts/logos_verse_4d_single_anchor_medoids_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_satellite_knn_drift_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _vec(row: dict[str, Any]) -> dict[str, float] | None:
    v = row.get("vector_4d")
    if not isinstance(v, dict):
        return None
    try:
        return {k: float(v[k]) for k in ("S", "L", "K", "M")}
    except (KeyError, TypeError, ValueError):
        return None


def _l2(a: dict[str, float], b: dict[str, float]) -> float:
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in ("S", "L", "K", "M")))


def _stats(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {"count": 0, "status": "no_rows"}
    s = sorted(vals)
    return {
        "count": len(s),
        "mean": sum(s) / len(s),
        "min": s[0],
        "max": s[-1],
        "p50": s[len(s) // 2],
        "p95": s[int(len(s) * 0.95)] if len(s) > 1 else s[-1],
        "status": "computed",
    }


def _medoid_id(path: Path) -> str | None:
    if not path.is_file():
        return None
    med = json.loads(path.read_text(encoding="utf-8"))
    vid = med.get("top_global_medoid")
    if vid:
        return str(vid)
    globals_ = med.get("global_medoids")
    if isinstance(globals_, list) and globals_ and isinstance(globals_[0], dict):
        return str(globals_[0].get("verse_id") or "")
    return None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--canon-jsonl", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--satellite-jsonl", type=Path, default=DEFAULT_APOCRYPHA)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--top-k", type=int, default=5, help="Report mean L2 of k nearest canon neighbors per satellite row")
    args = ap.parse_args()

    medoid_vid = _medoid_id(args.medoids_json)
    if not medoid_vid:
        print("missing medoid", file=sys.stderr)
        return 2

    canon_rows = _load_jsonl(args.canon_jsonl)
    if not canon_rows:
        print(f"missing canon: {args.canon_jsonl}", file=sys.stderr)
        return 2

    med_vec: dict[str, float] | None = None
    canon_vecs: list[tuple[str, dict[str, float]]] = []
    for row in canon_rows:
        v = _vec(row)
        vid = str(row.get("verse_id") or "")
        if not v or not vid:
            continue
        if vid == medoid_vid:
            med_vec = v
        canon_vecs.append((vid, v))
    if med_vec is None:
        print(f"medoid vector missing: {medoid_vid}", file=sys.stderr)
        return 2

    canon_l2 = [_l2(v, med_vec) for _, v in canon_vecs]
    canon_mean = sum(canon_l2) / len(canon_l2) if canon_l2 else 0.0

    sat_rows = _load_jsonl(args.satellite_jsonl)
    sat_direct_l2: list[float] = []
    sat_knn_l2: list[float] = []
    k = max(1, int(args.top_k))
    for row in sat_rows:
        sv = _vec(row)
        if not sv:
            continue
        sat_direct_l2.append(_l2(sv, med_vec))
        dists = sorted((_l2(sv, cv), vid) for vid, cv in canon_vecs)
        knn_mean = sum(d[0] for d in dists[:k]) / min(k, len(dists))
        sat_knn_l2.append(knn_mean)

    doc = {
        "schema": "logos_satellite_knn_drift_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "medoid_verse_id": medoid_vid,
        "canon": {
            "jsonl": str(args.canon_jsonl.relative_to(ROOT)).replace("\\", "/"),
            "row_count": len(canon_vecs),
            "l2_to_medoid": _stats(canon_l2),
        },
        "satellite": {
            "jsonl": str(args.satellite_jsonl.relative_to(ROOT)).replace("\\", "/"),
            "jsonl_present": args.satellite_jsonl.is_file(),
            "row_count": len(sat_rows),
            "l2_to_medoid": _stats(sat_direct_l2),
            "knn_mean_l2_to_canon": _stats(sat_knn_l2),
            "top_k": k,
        },
        "contrast": {
            "satellite_mean_minus_canon_mean": (
                (sum(sat_direct_l2) / len(sat_direct_l2) - canon_mean) if sat_direct_l2 else None
            ),
            "interpretation": (
                "[HYPO] Positive delta suggests satellite vectors sit farther from medoid "
                "than typical canon cloud — observational only."
            ),
        },
        "track_wall": {
            "merge_into_canon_complete_jsonl": False,
            "ready_for_external_send": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.output} sat_rows={len(sat_rows)} "
        f"sat_l2_mean={doc['satellite']['l2_to_medoid'].get('mean')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
