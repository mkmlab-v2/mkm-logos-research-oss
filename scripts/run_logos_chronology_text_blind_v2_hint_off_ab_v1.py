#!/usr/bin/env python3
"""Ablation: text_blind_v2 full vs text_blind_v2_no_hints (KO tags only, era hints off)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval_logos_chronology_era_blind_v1.py"
GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
CHRONO = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
OUT_V2 = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v2_v1_latest.json"
OUT_NOHINTS = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v2_no_hints_v1_latest.json"
OUT_AB = ROOT / "reports/logos_chronology_text_blind_v2_hint_off_ab_v1_latest.json"

from summarize_logos_chronology_partition_holdout_v1 import (  # noqa: E402
    PARTITIONS,
    _load,
    _partition_slice,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_eval(tag_mode: str, out_json: Path, modern_boost: float, boost_policy: str) -> tuple[int, dict[str, Any]]:
    cmd = [
        sys.executable,
        str(EVAL),
        "--gold-json",
        str(GOLD),
        "--chronology-json",
        str(CHRONO),
        "--output-json",
        str(out_json),
        "--tag-mode",
        tag_mode,
        "--modern-boost",
        str(modern_boost),
        "--boost-policy",
        boost_policy,
    ]
    print("+", " ".join(cmd), flush=True)
    rc = subprocess.call(cmd, cwd=str(ROOT))
    summary: dict[str, Any] = {}
    if out_json.is_file():
        doc = json.loads(out_json.read_text(encoding="utf-8"))
        summary = dict(doc.get("summary") or {})
    return rc, summary


def _compare_docs(full: dict[str, Any], no_hints: dict[str, Any]) -> dict[str, Any]:
    by_partition: dict[str, Any] = {}
    for part in PARTITIONS:
        s_full = _partition_slice(full, part)
        s_off = _partition_slice(no_hints, part)
        h_full = float(s_full.get("hit_at_1_strict") or 0.0)
        h_off = float(s_off.get("hit_at_1_strict") or 0.0)
        by_partition[part] = {
            "text_blind_v2_full": s_full,
            "text_blind_v2_no_hints": s_off,
            "delta_no_hints_minus_full": round(h_off - h_full, 6),
            "hint_uplift_full_minus_no_hints": round(h_full - h_off, 6),
        }
    hold = by_partition["train_holdout"]
    h_full = float((hold.get("text_blind_v2_full") or {}).get("hit_at_1_strict") or 0.0)
    h_off = float((hold.get("text_blind_v2_no_hints") or {}).get("hit_at_1_strict") or 0.0)
    sf = full.get("summary") or {}
    sn = no_hints.get("summary") or {}
    return {
        "all_events_hit_at_1_full": sf.get("hit_at_1_strict"),
        "all_events_hit_at_1_no_hints": sn.get("hit_at_1_strict"),
        "all_events_hint_uplift": round(
            float(sf.get("hit_at_1_strict") or 0.0) - float(sn.get("hit_at_1_strict") or 0.0),
            6,
        ),
        "train_holdout_hit_at_1_full": h_full,
        "train_holdout_hit_at_1_no_hints": h_off,
        "train_holdout_hint_uplift": round(h_full - h_off, 6),
        "by_partition": by_partition,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modern-boost", type=float, default=0.08)
    ap.add_argument("--boost-policy", default="tier_v1")
    ap.add_argument("--skip-v2-rerun", action="store_true", help="Reuse existing v2 full eval artifact")
    args = ap.parse_args()

    rc_full = 0
    s_full: dict[str, Any] = {}
    if args.skip_v2_rerun and OUT_V2.is_file():
        s_full = dict(_load(OUT_V2).get("summary") or {})
    else:
        rc_full, s_full = _run_eval("text_blind_v2", OUT_V2, args.modern_boost, args.boost_policy)

    rc_off, s_off = _run_eval(
        "text_blind_v2_no_hints", OUT_NOHINTS, args.modern_boost, args.boost_policy
    )
    if rc_full != 0 or rc_off != 0:
        return 1

    full_doc = _load(OUT_V2)
    off_doc = _load(OUT_NOHINTS)
    compare = _compare_docs(full_doc, off_doc)

    ab = {
        "schema": "logos_chronology_text_blind_v2_hint_off_ab_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "commander_approved": True,
        "policy": {
            "research_only": True,
            "non_gating": True,
            "ms_headline_unchanged": True,
            "ms_citation_still": "text_blind_tier_v1_only",
            "ablation": "era_text_hint_bonus disabled; KO keyword layer retained",
        },
        "inputs": {
            "gold_json": str(GOLD.relative_to(ROOT)).replace("\\", "/"),
            "modern_boost": args.modern_boost,
            "boost_policy": args.boost_policy,
        },
        "text_blind_v2_full": {
            "output_json": str(OUT_V2.relative_to(ROOT)).replace("\\", "/"),
            "summary": s_full,
        },
        "text_blind_v2_no_hints": {
            "output_json": str(OUT_NOHINTS.relative_to(ROOT)).replace("\\", "/"),
            "summary": s_off,
        },
        "compare": compare,
        "note_ko": (
            "hint-off=era phrase bonus 제거·KO 키워드만. MS baseline(v1) 교체 없음. "
            "hint_uplift=full−no_hints (양수면 hint layer 기여)."
        ),
    }
    OUT_AB.parent.mkdir(parents=True, exist_ok=True)
    OUT_AB.write_text(json.dumps(ab, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(compare, ensure_ascii=False, default=str))
    print(f"WROTE: {OUT_AB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
