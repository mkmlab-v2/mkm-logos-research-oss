#!/usr/bin/env python3
"""Audit unique mkm_advanced_insight diversity in interpret eval predictions (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/myeongri_interpret_narrative_diversity_audit_latest.json"
V3_PREFIX = "[HYPO] 결정론 엔진 기준 사주:"

_SKELETON_PATTERNS: list[tuple] = []


def _skeleton_patterns() -> list[tuple]:
    import re

    global _SKELETON_PATTERNS
    if not _SKELETON_PATTERNS:
        _SKELETON_PATTERNS = [
            (re.compile(r"년주 [^,]+"), "년주 {Y}"),
            (re.compile(r"월주 [^,]+"), "월주 {M}"),
            (re.compile(r"일주 [^,]+"), "일주 {D}"),
            (re.compile(r"시주 [^,]+"), "시주 {H}"),
            (re.compile(r"일간 [^.]+"), "일간 {DM}"),
            (re.compile(r"birth_instant_utc=[^,]+"), "birth_instant_utc={UTC}"),
            (re.compile(r"iana_tz=[^.]+"), "iana_tz={TZ}"),
        ]
    return _SKELETON_PATTERNS


def insight_to_template_skeleton(text: str) -> str:
    s = text.strip()
    for pat, repl in _skeleton_patterns():
        s = pat.sub(repl, s)
    return s


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_insight(raw: str) -> str | None:
    from scripts.run_myeongri_deterministic_lora_inference_eval_v1 import _extract_json_object
    from scripts.myeongri_interpret_envelope_views_v1 import (
        extract_mkm_insight_from_llm_parsed,
        sanitize_interpret_raw_for_parse,
    )

    parsed = _extract_json_object(sanitize_interpret_raw_for_parse(raw))
    if not isinstance(parsed, dict):
        return None
    return extract_mkm_insight_from_llm_parsed(parsed)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, required=True)
    ap.add_argument("--predictions-jsonl", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--v3-template-prefix", default=V3_PREFIX)
    args = ap.parse_args()

    eval_doc = json.loads(args.eval_json.read_text(encoding="utf-8"))
    preds = [
        json.loads(line)
        for line in args.predictions_jsonl.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    insights: list[str] = []
    empty_insight_rows = 0
    for p in preds:
        raw = p.get("prediction_raw", "")
        if not isinstance(raw, str):
            continue
        ins = _extract_insight(raw)
        if ins and ins.strip():
            insights.append(ins.strip())
        elif raw.strip():
            empty_insight_rows += 1

    n = len(insights)
    unique = len(set(insights))
    skeletons = [insight_to_template_skeleton(i) for i in insights]
    skeleton_unique = len(set(skeletons))
    v3_prefix_hits = sum(1 for i in insights if i.startswith(args.v3_template_prefix))
    narrative_gate_pass = skeleton_unique > 1 and (v3_prefix_hits / n if n else 0.0) < 0.5
    def _rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")

    report = {
        "schema": "myeongri_interpret_narrative_diversity_audit_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "eval_json": _rel(args.eval_json),
        "predictions_jsonl": _rel(args.predictions_jsonl),
        "rows_with_insight": n,
        "unique_insight_count": unique,
        "unique_insight_rate": round(unique / n, 6) if n else 0.0,
        "template_skeleton_unique_count": skeleton_unique,
        "template_skeleton_unique_rate": round(skeleton_unique / n, 6) if n else 0.0,
        "empty_insight_row_count": empty_insight_rows,
        "v3_fixed_prefix_rate": round(v3_prefix_hits / n, 6) if n else 0.0,
        "parse_ok_rate": eval_doc.get("parse_ok_rate"),
        "envelope_match_rate": eval_doc.get("envelope_match_rate"),
        "narrative_diversity_gate_pass": narrative_gate_pass,
        "interpretation": (
            "Full-string unique_insight_rate can stay 1.0 while template_skeleton_unique_count stays 1 "
            "(v3 curriculum: pillars vary, prose skeleton fixed). "
            "Use skeleton metrics + human_review for narrative quality; not Track A promotion."
            if skeleton_unique <= 1 and v3_prefix_hits == n
            else (
                "unique_insight_rate near 1.0 with low v3_fixed_prefix_rate suggests narrative diversity; "
                "match_rate may drop vs v3 oracle."
            )
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "unique_insight_rate": report["unique_insight_rate"], "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
