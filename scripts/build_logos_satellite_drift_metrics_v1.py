#!/usr/bin/env python3
"""L2 drift stats: canonical corpus vs MT-only gap verses relative to global medoid (B-track)."""

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
DEFAULT_MEDOIDS = ROOT / "docs/final/artifacts/logos_verse_4d_single_anchor_medoids_v1_latest.json"
DEFAULT_POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_satellite_drift_metrics_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _vec(row: dict[str, Any]) -> dict[str, float] | None:
    v = row.get("vector_4d") or row.get("unified_4d_vector")
    if not isinstance(v, dict):
        return None
    try:
        return {k: float(v[k]) for k in ("S", "L", "K", "M")}
    except (KeyError, TypeError, ValueError):
        return None


def _l2(a: dict[str, float], b: dict[str, float]) -> float:
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in ("S", "L", "K", "M")))


def _medoid_id(medoids_path: Path) -> str | None:
    if not medoids_path.is_file():
        return None
    med = json.loads(medoids_path.read_text(encoding="utf-8"))
    vid = med.get("top_global_medoid") or med.get("global_medoid_verse_id")
    if vid:
        return str(vid)
    globals_ = med.get("global_medoids")
    if isinstance(globals_, list) and globals_ and isinstance(globals_[0], dict):
        return str(globals_[0].get("verse_id") or "")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-jsonl", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--mt-only-policy-jsonl", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sample-max", type=int, default=0, help="0 = all rows")
    args = ap.parse_args()

    if not args.corpus_jsonl.is_file():
        print(f"missing corpus: {args.corpus_jsonl}", file=sys.stderr)
        return 2

    medoid_vid = _medoid_id(args.medoids_json)
    if not medoid_vid:
        print("missing medoid verse_id", file=sys.stderr)
        return 2

    index: dict[str, dict[str, Any]] = {}
    for line in args.corpus_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        vid = str(row.get("verse_id") or "").strip()
        if vid:
            index[vid] = row

    med_row = index.get(medoid_vid)
    med_vec = _vec(med_row) if med_row else None
    if not med_vec:
        print(f"medoid vector missing for {medoid_vid}", file=sys.stderr)
        return 2

    gap_ids: set[str] = set()
    if args.mt_only_policy_jsonl.is_file():
        for line in args.mt_only_policy_jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                gap_ids.add(str(json.loads(line)["verse_id"]))

    canon_l2: list[float] = []
    gap_l2: list[float] = []
    n = 0
    for vid, row in index.items():
        if args.sample_max and n >= args.sample_max:
            break
        v = _vec(row)
        if not v:
            continue
        d = _l2(v, med_vec)
        if vid in gap_ids:
            gap_l2.append(d)
        else:
            canon_l2.append(d)
        n += 1

    def _stats(vals: list[float]) -> dict[str, Any]:
        if not vals:
            return {"count": 0}
        s = sorted(vals)
        return {
            "count": len(s),
            "mean": sum(s) / len(s),
            "min": s[0],
            "max": s[-1],
            "p50": s[len(s) // 2],
            "p95": s[int(len(s) * 0.95)] if len(s) > 1 else s[-1],
        }

    doc = {
        "schema": "logos_satellite_drift_metrics_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "source_track": "B_ext",
        "medoid_verse_id": medoid_vid,
        "metric": "l2_vector_4d_to_medoid",
        "canon_population": _stats(canon_l2),
        "mt_only_gap_population": _stats(gap_l2),
        "interpretation": (
            "[HYPO] MT-only gap verses are geometrically distinct from the SBLGNT/BHS-filled "
            "corpus cloud in gematria_bridge_v1 space — observational, not textual TR distance."
        ),
        "track_wall": {
            "merge_into_complete_jsonl": False,
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.output} medoid={medoid_vid} "
        f"canon_n={doc['canon_population'].get('count')} gap_n={doc['mt_only_gap_population'].get('count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
