#!/usr/bin/env python3
"""B-track: queue verses with pipeline4 fallback vector (0.25^4) for re-encode review.

Does not run encoder or mutate verse_decoded / Track A. Export-only backlog.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.myeongni.gematria_myeongri_math_v1 import coerce_4d

FULL = ROOT / "data/logos/verse_4pipeline_full_31102.json"
JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
OUT_JSONL = ROOT / "reports/logos_4d_fallback_reencode_queue_v1_latest.jsonl"
OUT_META = ROOT / "reports/logos_4d_fallback_reencode_queue_v1_latest.json"
AUDIT = ROOT / "reports/logos_4pipeline_jsonl_4d_cross_audit_v1_latest.json"
FALLBACK_KEY = (0.25, 0.25, 0.25, 0.25)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _iter_full(path: Path) -> Iterator[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("expected top-level JSON array")
    for row in data:
        if isinstance(row, dict):
            yield row


def _pipe_vec(row: dict[str, Any]) -> dict[str, float] | None:
    p4 = row.get("pipeline4_unified_v2") or {}
    raw = p4.get("vector_4d") if isinstance(p4, dict) else None
    return coerce_4d(raw) if isinstance(raw, dict) else None


def _is_fallback(v: dict[str, float], places: int) -> bool:
    key = tuple(round(v[k], places) for k in ("S", "L", "K", "M"))
    return key == FALLBACK_KEY


def _load_jsonl_fallback_ids(path: Path, places: int) -> set[str]:
    out: set[str] = set()
    if not path.is_file():
        return out
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if not vid:
                continue
            v = coerce_4d(row.get("vector_4d") or row.get("unified_4d_vector") or {})
            if _is_fallback(v, places):
                out.add(vid)
    return out


def build_queue(
    *,
    full: Path,
    jsonl: Path | None,
    places: int,
    max_rows: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    j_fallback = _load_jsonl_fallback_ids(jsonl, places) if jsonl else set()
    rows: list[dict[str, Any]] = []
    counts = {
        "pipeline_fallback": 0,
        "jsonl_also_fallback": 0,
        "jsonl_non_fallback": 0,
        "missing_jsonl": 0,
    }
    for row in _iter_full(full):
        vid = str(row.get("verse_id") or "").strip()
        pv = _pipe_vec(row)
        if not vid or pv is None or not _is_fallback(pv, places):
            continue
        counts["pipeline_fallback"] += 1
        in_j = vid in j_fallback if jsonl and jsonl.is_file() else None
        if in_j is True:
            counts["jsonl_also_fallback"] += 1
        elif in_j is False:
            counts["jsonl_non_fallback"] += 1
        elif jsonl and jsonl.is_file():
            counts["missing_jsonl"] += 1
        preview = row.get("text_preview") or row.get("text") or ""
        rows.append(
            {
                "verse_id": vid,
                "queue_status": "pending_pipeline4_reencode",
                "hypothesis_tier": "B",
                "research_only": True,
                "boundary_ack": True,
                "reason": "pipeline4_unified_v2_fallback_vector_025",
                "pipeline4_vector_4d": {k: round(pv[k], 6) for k in pv},
                "jsonl_also_fallback": in_j,
                "text_preview": str(preview)[:240],
                "source": "verse_4pipeline_full_31102",
            }
        )
        if max_rows > 0 and len(rows) >= max_rows:
            break
    return rows, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", type=Path, default=FULL)
    ap.add_argument("--jsonl", type=Path, default=JSONL)
    ap.add_argument("--out-jsonl", type=Path, default=OUT_JSONL)
    ap.add_argument("--out-meta", type=Path, default=OUT_META)
    ap.add_argument("--round-places", type=int, default=4)
    ap.add_argument("--max-rows", type=int, default=0)
    ap.add_argument("--skip-jsonl-compare", action="store_true")
    args = ap.parse_args()
    if not args.full.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.full}"}))
        return 2
    jpath = None if args.skip_jsonl_compare else args.jsonl
    rows, counts = build_queue(
        full=args.full, jsonl=jpath, places=max(1, args.round_places), max_rows=max(0, args.max_rows)
    )
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    meta = {
        "schema": "logos_4d_fallback_reencode_queue_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "boundary_ack": True,
        "fact_lock": {"compression_track_a_touch": False, "apply_gematria_4d_bridge_policy": False},
        "inputs": {"full_pipeline_json": _rel(args.full), "jsonl": _rel(jpath) if jpath else None},
        "round_places": args.round_places,
        "fallback_key": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        "counts": {**counts, "rows_queued": len(rows)},
        "out_jsonl": _rel(args.out_jsonl),
        "audit_pointer": _rel(AUDIT) if AUDIT.is_file() else None,
        "operator_hint": "Review queue only — run encoder separately; do not merge into Track A.",
        "track_wall": {"a_track_auto_promotion": False, "ready_for_external_send": False},
    }
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows), **counts, "out": str(args.out_meta)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
