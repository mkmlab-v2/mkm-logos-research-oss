#!/usr/bin/env python3
"""Off-fixture era blind AB: text_blind v1 (MS) vs v2 (+ optional no_hints) on disjoint news cohort."""

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
BUILD_GOLD = ROOT / "scripts/build_logos_chronology_off_fixture_era_gold_v1.py"
GOLD = ROOT / "docs/final/artifacts/logos_chronology_off_fixture_era_gold_v1_latest.json"
CHRONO = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
OUT_V1 = ROOT / "docs/final/artifacts/logos_chronology_off_fixture_eval_text_blind_v1_latest.json"
OUT_V2 = ROOT / "docs/final/artifacts/logos_chronology_off_fixture_eval_text_blind_v2_v1_latest.json"
OUT_V2_NH = ROOT / "docs/final/artifacts/logos_chronology_off_fixture_eval_text_blind_v2_no_hints_v1_latest.json"
OUT_AB = ROOT / "reports/logos_chronology_off_fixture_text_blind_v2_ab_v1_latest.json"
OUT_HOLDOUT = ROOT / "reports/logos_chronology_off_fixture_holdout_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


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
    rc = _run(cmd)
    summary: dict[str, Any] = {}
    if out_json.is_file():
        doc = json.loads(out_json.read_text(encoding="utf-8"))
        summary = dict(doc.get("summary") or {})
    return rc, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modern-boost", type=float, default=0.08)
    ap.add_argument("--boost-policy", default="tier_v1")
    ap.add_argument("--target-hit-at-1", type=float, default=0.15)
    ap.add_argument("--skip-gold-build", action="store_true")
    ap.add_argument("--include-no-hints", action="store_true", help="Also run text_blind_v2_no_hints lane")
    ap.add_argument("--max-expansion-rows", type=int, default=40)
    args = ap.parse_args()

    if not args.skip_gold_build:
        rc_g = _run(
            [
                sys.executable,
                str(BUILD_GOLD),
                "--max-expansion-rows",
                str(args.max_expansion_rows),
            ]
        )
        if rc_g != 0:
            return rc_g

    if not GOLD.is_file():
        print(f"MISSING: {GOLD}", file=sys.stderr)
        return 2

    gold_doc = json.loads(GOLD.read_text(encoding="utf-8"))
    rc1, s1 = _run_eval("text_blind", OUT_V1, args.modern_boost, args.boost_policy)
    rc2, s2 = _run_eval("text_blind_v2", OUT_V2, args.modern_boost, args.boost_policy)
    rc3 = 0
    s3: dict[str, Any] = {}
    if args.include_no_hints:
        rc3, s3 = _run_eval("text_blind_v2_no_hints", OUT_V2_NH, args.modern_boost, args.boost_policy)

    h1 = float(s1.get("hit_at_1_strict") or 0.0)
    h2 = float(s2.get("hit_at_1_strict") or 0.0)
    delta = round(h2 - h1, 6)

    rc_h = _run(
        [
            sys.executable,
            str(ROOT / "scripts/summarize_logos_chronology_off_fixture_holdout_v1.py"),
        ]
    )

    ab: dict[str, Any] = {
        "schema": "logos_chronology_off_fixture_text_blind_v2_ab_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "ms_headline_unchanged": True,
            "ms_citation_still": "text_blind_tier_v1_only",
            "cohort": "off_fixture_disjoint_from_historical_47",
        },
        "inputs": {
            "gold_json": str(GOLD.relative_to(ROOT)).replace("\\", "/"),
            "cohort_definition": gold_doc.get("cohort_definition") or {},
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
            "all_events_hit_at_1_v1": h1,
            "all_events_hit_at_1_v2": h2,
            "delta_v2_minus_v1": delta,
            "target_hit_at_1": args.target_hit_at_1,
            "target_met": h2 >= args.target_hit_at_1,
            "off_fixture_measured": True,
        },
        "note_ko": (
            "historical gold 47건과 event_id 불교집 off-fixture cohort. "
            "hardset v2 + blind_split OOV expansion. MS ~6.4% baseline 교체 금지."
        ),
    }
    if args.include_no_hints:
        h3 = float(s3.get("hit_at_1_strict") or 0.0)
        ab["text_blind_v2_no_hints_btrack_poc"] = {
            "exit_code": rc3,
            "output_json": str(OUT_V2_NH.relative_to(ROOT)).replace("\\", "/"),
            "summary": s3,
        }
        ab["compare"]["all_events_hit_at_1_v2_no_hints"] = h3
        ab["compare"]["hint_uplift_all_events"] = round(h2 - h3, 6)

    OUT_AB.parent.mkdir(parents=True, exist_ok=True)
    OUT_AB.write_text(json.dumps(ab, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(ab["compare"], ensure_ascii=False))

    ok = rc1 == 0 and rc2 == 0 and rc_h == 0 and (rc3 == 0 if args.include_no_hints else True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
