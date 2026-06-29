#!/usr/bin/env python3
"""B-track: propose pipeline4 vector fixes from jsonl for fallback-queue verses.

Does not overwrite verse_4pipeline_full_31102.json — emits patch JSONL + status only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.myeongni.gematria_myeongri_math_v1 import coerce_4d

QUEUE = ROOT / "reports/logos_4d_fallback_reencode_queue_v1_latest.jsonl"
JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
PATCH_OUT = ROOT / "reports/logos_4pipeline_4d_fallback_patch_v1_latest.jsonl"
STATUS_OUT = ROOT / "reports/logos_4d_fallback_reencode_status_v1_latest.json"
FALLBACK_KEY = (0.25, 0.25, 0.25, 0.25)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _is_fallback(v: dict[str, float], places: int) -> bool:
    key = tuple(round(v[k], places) for k in ("S", "L", "K", "M"))
    return key == FALLBACK_KEY


def _load_jsonl(path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if vid:
                out[vid] = coerce_4d(row.get("vector_4d") or row.get("unified_4d_vector") or {})
    return out


def reconcile(
    *,
    queue_path: Path,
    jsonl_path: Path,
    places: int,
    max_rows: int,
) -> tuple[list[dict], list[dict], dict[str, int]]:
    jidx = _load_jsonl(jsonl_path)
    patched: list[dict] = []
    pending: list[dict] = []
    counts = {
        "queue_rows_read": 0,
        "patched_from_jsonl": 0,
        "pending_encoder": 0,
        "missing_jsonl": 0,
    }
    with queue_path.open(encoding="utf-8") as f:
        for line in f:
            if max_rows > 0 and counts["queue_rows_read"] >= max_rows:
                break
            q = json.loads(line)
            counts["queue_rows_read"] += 1
            vid = str(q.get("verse_id") or "")
            if not vid:
                continue
            old = coerce_4d(q.get("pipeline4_vector_4d") or {})
            if vid not in jidx:
                counts["missing_jsonl"] += 1
                pending.append({"verse_id": vid, "reason": "missing_in_jsonl"})
                continue
            nv = jidx[vid]
            if _is_fallback(nv, places):
                counts["pending_encoder"] += 1
                pending.append(
                    {
                        "verse_id": vid,
                        "reason": "jsonl_also_fallback",
                        "jsonl_vector_4d": {k: round(nv[k], 6) for k in nv},
                    }
                )
                continue
            counts["patched_from_jsonl"] += 1
            patched.append(
                {
                    "verse_id": vid,
                    "patch_status": "proposed_pipeline4_from_jsonl",
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "reconcile_method": "jsonl_vector_copy",
                    "pipeline4_vector_4d_before": {k: round(old[k], 6) for k in old},
                    "pipeline4_vector_4d_after": {k: round(nv[k], 6) for k in nv},
                }
            )
    return patched, pending, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-jsonl", type=Path, default=QUEUE)
    ap.add_argument("--jsonl", type=Path, default=JSONL)
    ap.add_argument("--patch-out", type=Path, default=PATCH_OUT)
    ap.add_argument("--status-out", type=Path, default=STATUS_OUT)
    ap.add_argument("--pending-out", type=Path, default=None)
    ap.add_argument("--round-places", type=int, default=4)
    ap.add_argument("--max-rows", type=int, default=0)
    args = ap.parse_args()
    if not args.queue_jsonl.is_file() or not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": "missing queue or jsonl"}))
        return 2
    patched, pending, counts = reconcile(
        queue_path=args.queue_jsonl,
        jsonl_path=args.jsonl,
        places=max(1, args.round_places),
        max_rows=max(0, args.max_rows),
    )
    args.patch_out.parent.mkdir(parents=True, exist_ok=True)
    with args.patch_out.open("w", encoding="utf-8") as fh:
        for row in patched:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    pending_out = args.pending_out or (args.status_out.parent / "logos_4d_pending_encoder_v1_latest.json")
    pending_out.write_text(
        json.dumps(
            {
                "schema": "logos_4d_pending_encoder_v1",
                "generated_at_utc": _utc(),
                "count": len(pending),
                "verses": pending,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    status = {
        "schema": "logos_4d_fallback_reencode_status_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "boundary_ack": True,
        "fact_lock": {
            "compression_track_a_touch": False,
            "apply_gematria_4d_bridge_policy": False,
            "full_pipeline_mutated": False,
        },
        "inputs": {
            "queue_jsonl": _rel(args.queue_jsonl),
            "jsonl": _rel(args.jsonl),
            "patch_jsonl": _rel(args.patch_out),
            "pending_encoder_json": _rel(pending_out),
        },
        "counts": counts,
        "expected_pipeline4_fallback_after_patch_apply": counts["pending_encoder"],
        "pending_encoder_sample": pending[:20],
        "operator_hint": (
            "Apply patch to verse_4pipeline_full_31102.json in a separate approved step; "
            f"{counts['pending_encoder']} verses still need true re-encode."
        ),
        "track_wall": {"a_track_auto_promotion": False, "ready_for_external_send": False},
    }
    args.status_out.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **counts, "patch_out": str(args.patch_out), "status_out": str(args.status_out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
