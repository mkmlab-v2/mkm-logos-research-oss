#!/usr/bin/env python3
"""Run historical era blind AB: text_blind v1 (MS baseline) vs text_blind_v2 (B-track PoC)."""
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
OUT_V1 = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v1_latest.json"
OUT_V2 = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v2_v1_latest.json"
OUT_AB = ROOT / "reports/logos_chronology_text_blind_v2_ab_v1_latest.json"


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modern-boost", type=float, default=0.08)
    ap.add_argument("--boost-policy", default="tier_v1")
    ap.add_argument("--target-hit-at-1", type=float, default=0.15)
    args = ap.parse_args()

    rc1, s1 = _run_eval("text_blind", OUT_V1, args.modern_boost, args.boost_policy)
    rc2, s2 = _run_eval("text_blind_v2", OUT_V2, args.modern_boost, args.boost_policy)
    h1 = float(s1.get("hit_at_1_strict") or 0.0)
    h2 = float(s2.get("hit_at_1_strict") or 0.0)
    delta = round(h2 - h1, 6)
    ab = {
        "schema": "logos_chronology_text_blind_v2_ab_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "ms_headline_unchanged": True,
            "ms_citation_still": "text_blind_tier_v1_only",
        },
        "inputs": {
            "gold_json": str(GOLD.relative_to(ROOT)).replace("\\", "/"),
            "modern_boost": args.modern_boost,
            "boost_policy": args.boost_policy,
        },
        "text_blind_v1_ms_baseline": {
            "exit_code": rc1,
            "output_json": str(OUT_V1.relative_to(ROOT)).replace("\\", "/"),
            "summary": s1,
        },
        "text_blind_v2_btrack_poc": {
            "exit_code": rc2,
            "output_json": str(OUT_V2.relative_to(ROOT)).replace("\\", "/"),
            "summary": s2,
        },
        "compare": {
            "hit_at_1_strict_v1": h1,
            "hit_at_1_strict_v2": h2,
            "delta_v2_minus_v1": delta,
            "target_hit_at_1": args.target_hit_at_1,
            "target_met": h2 >= args.target_hit_at_1,
        },
        "note_ko": "v2=KO keyword+era hint layer only; MS/대외 6.4% baseline 교체 금지 until commander sign-off on new eval contract.",
    }
    OUT_AB.parent.mkdir(parents=True, exist_ok=True)
    OUT_AB.write_text(json.dumps(ab, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(ab["compare"], ensure_ascii=False))
    return 0 if rc1 == 0 and rc2 == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
