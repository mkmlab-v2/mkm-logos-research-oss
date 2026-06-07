#!/usr/bin/env python3
"""Partition-sliced holdout compare for text_blind v1 (MS) vs v2 (B-track PoC)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
REP = ROOT / "reports"
DEFAULT_V1 = ART / "logos_chronology_era_blind_eval_text_blind_v1_latest.json"
DEFAULT_V2 = ART / "logos_chronology_era_blind_eval_text_blind_v2_v1_latest.json"
DEFAULT_OUT = REP / "logos_chronology_text_blind_v2_holdout_v1_latest.json"
PARTITIONS = ("train_holdout", "locked_eval", "calibration")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rate(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [r for r in rows if r.get(key) is not None]
    if not vals:
        return None
    hits = sum(1 for r in vals if r.get(key))
    return round(hits / len(vals), 6)


def _partition_slice(doc: dict[str, Any], partition: str) -> dict[str, Any]:
    rows = [
        r
        for r in (doc.get("rows") or [])
        if not r.get("is_synthetic_source") and str(r.get("partition") or "") == partition
    ]
    macro = [r for r in rows if r.get("tier") == "macro_landmark"]
    narrative = [r for r in rows if r.get("tier") == "biblical_narrative"]
    return {
        "partition": partition,
        "n": len(rows),
        "hit_at_1_strict": _rate(rows, "hit_at_1_strict"),
        "hit_at_1_relaxed": _rate(rows, "hit_at_1_relaxed"),
        "hit_at_3": _rate(rows, "hit_at_3"),
        "macro_landmark_hit_at_1_strict": _rate(macro, "hit_at_1_strict"),
        "narrative_hit_at_1_strict": _rate(narrative, "hit_at_1_strict"),
    }


def build_holdout(v1: dict[str, Any], v2: dict[str, Any]) -> dict[str, Any]:
    by_partition: dict[str, dict[str, Any]] = {}
    for part in PARTITIONS:
        s1 = _partition_slice(v1, part)
        s2 = _partition_slice(v2, part)
        h1 = float(s1.get("hit_at_1_strict") or 0.0)
        h2 = float(s2.get("hit_at_1_strict") or 0.0)
        by_partition[part] = {
            "text_blind_v1_ms_baseline": s1,
            "text_blind_v2_btrack_poc": s2,
            "delta_v2_minus_v1": round(h2 - h1, 6),
            "primary_holdout": part == "train_holdout",
        }
    hold = by_partition["train_holdout"]
    h_hold_v2 = float((hold.get("text_blind_v2_btrack_poc") or {}).get("hit_at_1_strict") or 0.0)
    return {
        "schema": "logos_chronology_text_blind_v2_holdout_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "ms_headline_unchanged": True,
            "ms_citation_still": "text_blind_tier_v1_only",
            "primary_oos_partition": "train_holdout",
        },
        "inputs": {
            "v1_json": str(DEFAULT_V1.relative_to(ROOT)).replace("\\", "/"),
            "v2_json": str(DEFAULT_V2.relative_to(ROOT)).replace("\\", "/"),
        },
        "all_events_summary": {
            "text_blind_v1_ms_baseline": v1.get("summary") or {},
            "text_blind_v2_btrack_poc": v2.get("summary") or {},
        },
        "by_partition": by_partition,
        "compare": {
            "train_holdout_hit_at_1_v1": (hold.get("text_blind_v1_ms_baseline") or {}).get("hit_at_1_strict"),
            "train_holdout_hit_at_1_v2": (hold.get("text_blind_v2_btrack_poc") or {}).get("hit_at_1_strict"),
            "train_holdout_delta_v2_minus_v1": hold.get("delta_v2_minus_v1"),
            "train_holdout_target_15pct_met": h_hold_v2 >= 0.15,
        },
        "note_ko": (
            "train_holdout=20건 OOS-style slice. v2는 B-track 연구; MS/대외 6.4% baseline 교체 금지."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v1-json", type=Path, default=DEFAULT_V1)
    ap.add_argument("--v2-json", type=Path, default=DEFAULT_V2)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    v1_path = args.v1_json if args.v1_json.is_absolute() else ROOT / args.v1_json
    v2_path = args.v2_json if args.v2_json.is_absolute() else ROOT / args.v2_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    doc = build_holdout(_load(v1_path), _load(v2_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc["compare"], ensure_ascii=False))
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
