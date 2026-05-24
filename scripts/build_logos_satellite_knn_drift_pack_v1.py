#!/usr/bin/env python3
"""Per-satellite kNN drift pack (apocrypha + DSS lanes) — B-track, no canon merge."""

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

DEFAULT_CANON = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_single_anchor_v1_latest.jsonl"
DEFAULT_MEDOIDS = ROOT / "docs/final/artifacts/logos_verse_4d_single_anchor_medoids_v1_latest.json"
DEFAULT_OUT_PACK = ROOT / "docs/final/artifacts/logos_satellite_knn_drift_pack_v1_latest.json"
DEFAULT_OUT_APOCRYPHA_LEGACY = ROOT / "docs/final/artifacts/logos_satellite_knn_drift_v1_latest.json"

SATELLITES: tuple[tuple[str, str], ...] = (
    ("apocrypha", "reports/constitution/btrack_pilot/logos_verse_4d_apocrypha_lane_v1_latest.jsonl"),
    ("dss", "reports/constitution/btrack_pilot/logos_verse_4d_dss_lane_v1_latest.jsonl"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


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


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _medoid_id(path: Path) -> str | None:
    if not path.is_file():
        return None
    med = json.loads(path.read_text(encoding="utf-8"))
    vid = med.get("top_global_medoid") or med.get("global_medoid_verse_id")
    if vid:
        return str(vid)
    globals_ = med.get("global_medoids")
    if isinstance(globals_, list) and globals_ and isinstance(globals_[0], dict):
        return str(globals_[0].get("verse_id") or "")
    return None


def _compute_satellite_knn(
    *,
    corpus_type: str,
    satellite_jsonl: Path,
    canon_rows: list[dict[str, Any]],
    canon_vecs: list[tuple[str, dict[str, float]]],
    med_vec: dict[str, float],
    canon_mean: float,
    top_k: int,
) -> dict[str, Any]:
    sat_rows = _load_jsonl(satellite_jsonl)
    sat_direct_l2: list[float] = []
    sat_knn_l2: list[float] = []
    k = max(1, top_k)
    for row in sat_rows:
        sv = _vec(row)
        if not sv:
            continue
        sat_direct_l2.append(_l2(sv, med_vec))
        dists = sorted((_l2(sv, cv), vid) for vid, cv in canon_vecs)
        knn_mean = sum(d[0] for d in dists[:k]) / min(k, len(dists))
        sat_knn_l2.append(knn_mean)

    return {
        "corpus_type": corpus_type,
        "jsonl": _rel(satellite_jsonl),
        "jsonl_present": satellite_jsonl.is_file(),
        "row_count": len(sat_rows),
        "vectors_used": len(sat_direct_l2),
        "l2_to_medoid": _stats(sat_direct_l2),
        "knn_mean_l2_to_canon": _stats(sat_knn_l2),
        "top_k": k,
        "contrast_delta": (
            (sum(sat_direct_l2) / len(sat_direct_l2) - canon_mean) if sat_direct_l2 else None
        ),
        "status": "computed" if sat_direct_l2 else "pending_ingest",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--canon-jsonl", type=Path, default=DEFAULT_CANON)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--output-pack", type=Path, default=DEFAULT_OUT_PACK)
    ap.add_argument("--legacy-apocrypha-out", type=Path, default=DEFAULT_OUT_APOCRYPHA_LEGACY)
    ap.add_argument("--top-k", type=int, default=5)
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

    per_sat: dict[str, Any] = {}
    for corpus_type, rel_path in SATELLITES:
        sat_path = ROOT / rel_path
        per_sat[corpus_type] = _compute_satellite_knn(
            corpus_type=corpus_type,
            satellite_jsonl=sat_path,
            canon_rows=canon_rows,
            canon_vecs=canon_vecs,
            med_vec=med_vec,
            canon_mean=canon_mean,
            top_k=int(args.top_k),
        )

    pack = {
        "schema": "logos_satellite_knn_drift_pack_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "medoid_verse_id": medoid_vid,
        "canon": {
            "jsonl": _rel(args.canon_jsonl),
            "row_count": len(canon_vecs),
            "l2_to_medoid": _stats(canon_l2),
        },
        "satellites": per_sat,
        "track_wall": {
            "merge_into_canon_complete_jsonl": False,
            "ready_for_external_send": False,
        },
    }
    args.output_pack.parent.mkdir(parents=True, exist_ok=True)
    args.output_pack.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    apo = per_sat.get("apocrypha") or {}
    legacy = {
        "schema": "logos_satellite_knn_drift_v1",
        "version": "1.0.0",
        "ts_utc": pack["ts_utc"],
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "medoid_verse_id": medoid_vid,
        "canon": pack["canon"],
        "satellite": {
            "jsonl": apo.get("jsonl"),
            "jsonl_present": apo.get("jsonl_present"),
            "row_count": apo.get("row_count"),
            "l2_to_medoid": apo.get("l2_to_medoid"),
            "knn_mean_l2_to_canon": apo.get("knn_mean_l2_to_canon"),
            "top_k": apo.get("top_k"),
        },
        "contrast": {
            "satellite_mean_minus_canon_mean": apo.get("contrast_delta"),
            "interpretation": (
                "[HYPO] Positive delta suggests satellite vectors sit farther from medoid "
                "than typical canon cloud — observational only."
            ),
        },
        "track_wall": pack["track_wall"],
        "pack_ref": _rel(args.output_pack),
    }
    args.legacy_apocrypha_out.parent.mkdir(parents=True, exist_ok=True)
    args.legacy_apocrypha_out.write_text(json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"wrote {args.output_pack} "
        f"apo={apo.get('vectors_used')} dss={(per_sat.get('dss') or {}).get('vectors_used')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
