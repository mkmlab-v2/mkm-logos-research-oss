#!/usr/bin/env python3
"""Heuristic B-track reviewer verdicts for v5 calibration30 (not commander-signed)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_interpret_envelope_views_v1 import (  # noqa: E402
    _hour_pillar_cited,
    extract_compact_from_interpret_instruction,
)

DEFAULT_SAMPLE = ROOT / "reports/myeongri_interpret_v5_human_review_calibration30_latest.json"
DEFAULT_SFT = ROOT / "data/training/myeongri_interpret_sft_v5/locked_eval.jsonl"

_OVERCONF = re.compile(r"(정확한\s*해석|확실|확定적|모든\s*정보가\s*일치)")


def _banned_price_med(insight: str) -> bool:
    if re.search(r"(매수|매도|투자\s*추천|처방|수술\s*필)", insight, re.I):
        return True
    if re.search(r"진단", insight, re.I) and not re.search(
        r"(진단\s*아님|의료\s*진단[·\s]*투자|진단[·\s]*투자\s*단정\s*금지)", insight, re.I
    ):
        return True
    return False


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _heuristic_verdict(
    insight: str,
    *,
    gold_insight_head: str,
    compact: dict[str, Any] | None,
) -> tuple[str, str]:
    if not insight.strip():
        return "fail", "empty_insight"
    if _banned_price_med(insight):
        return "fail", "price_med_banned"
    if _OVERCONF.search(insight):
        return "needs_edit", "overconfidence_phrase"
    if gold_insight_head and re.search(r"시[\s\w가-힣]{2}", gold_insight_head):
        if not _hour_pillar_cited(insight):
            return "needs_edit", "missing_hour_pillar"
    if compact:
        fs = compact.get("full_saju") if isinstance(compact.get("full_saju"), dict) else {}
        saju = fs.get("saju") if isinstance(fs.get("saju"), dict) else {}
        pillars = [saju.get(k) for k in ("year", "month", "day", "hour") if saju.get(k)]
        if len(pillars) >= 4:
            cited = sum(1 for p in pillars if str(p) in insight)
            if cited < 3:
                return "needs_edit", "under_cited_pillars"
    return "pass", "heuristic_ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-json", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--sft-jsonl", type=Path, default=DEFAULT_SFT)
    args = ap.parse_args()

    if not args.sample_json.is_file() or not args.sft_jsonl.is_file():
        print(json.dumps({"ok": False, "error": "missing inputs"}))
        return 2

    sft_rows = [
        json.loads(l)
        for l in args.sft_jsonl.read_text(encoding="utf-8-sig").splitlines()
        if l.strip()
    ]
    doc = json.loads(args.sample_json.read_text(encoding="utf-8"))
    counts = {"pass": 0, "fail": 0, "needs_edit": 0}

    for s in doc.get("samples") or []:
        ri = int(s["row_index"])
        sft_row = sft_rows[ri - 1]
        compact = extract_compact_from_interpret_instruction(str(sft_row.get("instruction", "")))
        gold_head = str(s.get("gold_insight_head") or "")
        insight = str(s.get("mkm_advanced_insight") or "")
        verdict, reason = _heuristic_verdict(insight, gold_insight_head=gold_head, compact=compact)
        s["reviewer_verdict"] = verdict
        s["reviewer_verdict_source"] = "heuristic_v5_calibration30_v1"
        s["reviewer_verdict_reason"] = reason
        s["reviewer_comment"] = f"[heuristic] {reason}"
        counts[verdict] = counts.get(verdict, 0) + 1

    now = _utc_now()
    doc["human_verdict_counts"] = counts
    doc["human_verdict_applied_at_utc"] = now
    doc["human_verdict_source"] = "apply_myeongri_interpret_v5_calibration30_heuristic_review_v1.py"
    doc["calibration_gate_pass"] = counts.get("fail", 0) == 0 and counts.get("needs_edit", 0) == 0
    policy = doc.setdefault("calibration_policy_v1", {})
    policy["pending_reviewer_verdict_count"] = 0
    policy["human_verdict_counts"] = counts
    policy["calibration_gate_pass"] = doc["calibration_gate_pass"]
    policy["phase"] = "v5_calibration30_heuristic_reviewed"

    args.sample_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "counts": counts, "calibration_gate_pass": doc["calibration_gate_pass"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
