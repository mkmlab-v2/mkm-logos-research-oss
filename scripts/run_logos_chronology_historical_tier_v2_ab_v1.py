#!/usr/bin/env python3
"""Historical era gold: text_blind tier_v1 vs tier_v2_locked_eval AB ([HYPO], NON_GATING)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
EVAL = ROOT / "scripts/eval_logos_chronology_era_blind_v1.py"
DEFAULT_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_chronology_historical_tier_v2_ab_v1_latest.json"
ART = ROOT / "docs/final/artifacts"


def _run_eval(gold: Path, tag_mode: str, policy: str, out: Path) -> dict[str, Any]:
    cmd = [
        PY,
        str(EVAL),
        "--gold-json",
        str(gold),
        "--tag-mode",
        tag_mode,
        "--modern-boost",
        "0.08",
        "--boost-policy",
        policy,
        "--output-json",
        str(out),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary: dict[str, Any] = {}
    status = None
    if out.is_file():
        doc = json.loads(out.read_text(encoding="utf-8-sig"))
        summary = dict(doc.get("summary") or {})
        status = doc.get("status")
    return {
        "exit_code": cp.returncode,
        "status": status,
        "summary": summary,
        "output_json": str(out.relative_to(ROOT)).replace("\\", "/"),
    }


def _f(step: dict[str, Any], key: str) -> float | None:
    v = (step.get("summary") or {}).get(key)
    return float(v) if v is not None else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gold = args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json
    steps = {
        "text_blind_tier_v1": _run_eval(
            gold,
            "text_blind",
            "tier_v1",
            ART / "logos_chronology_era_blind_eval_text_blind_v1_latest.json",
        ),
        "text_blind_tier_v2": _run_eval(
            gold,
            "text_blind",
            "tier_v2_locked_eval",
            ART / "logos_chronology_era_blind_eval_text_blind_tier_v2_v1_latest.json",
        ),
        "gold_tags_tier_v1": _run_eval(
            gold,
            "gold_tags",
            "tier_v1",
            ART / "logos_chronology_era_blind_eval_v1_latest.json",
        ),
        "gold_tags_tier_v2": _run_eval(
            gold,
            "gold_tags",
            "tier_v2_locked_eval",
            ART / "logos_chronology_era_blind_eval_gold_tags_tier_v2_v1_latest.json",
        ),
    }

    tb1 = _f(steps["text_blind_tier_v1"], "hit_at_1_strict")
    tb2 = _f(steps["text_blind_tier_v2"], "hit_at_1_strict")
    compare = {
        "ms_citation_baseline_text_blind_tier_v1": tb1,
        "text_blind_tier_v2_hit_at_1_strict": tb2,
        "text_blind_delta_v2_minus_v1": round(tb2 - tb1, 6) if tb1 is not None and tb2 is not None else None,
        "text_blind_locked_eval_tier_v1": _f(steps["text_blind_tier_v1"], "locked_eval_hit_at_1_strict"),
        "text_blind_locked_eval_tier_v2": _f(steps["text_blind_tier_v2"], "locked_eval_hit_at_1_strict"),
        "gold_tags_tier_v1_hit_at_1": _f(steps["gold_tags_tier_v1"], "hit_at_1_strict"),
        "gold_tags_tier_v2_hit_at_1": _f(steps["gold_tags_tier_v2"], "hit_at_1_strict"),
        "gold_tags_delta_v2_minus_v1": (
            round(
                _f(steps["gold_tags_tier_v2"], "hit_at_1_strict") - _f(steps["gold_tags_tier_v1"], "hit_at_1_strict"),
                6,
            )
            if _f(steps["gold_tags_tier_v2"], "hit_at_1_strict") is not None
            and _f(steps["gold_tags_tier_v1"], "hit_at_1_strict") is not None
            else None
        ),
    }

    contaminated = (
        compare["text_blind_delta_v2_minus_v1"] is not None
        and abs(compare["text_blind_delta_v2_minus_v1"]) > 0.001
    )
    ok = all(v.get("exit_code") == 0 for v in steps.values())
    doc = {
        "schema": "logos_chronology_historical_tier_v2_ab_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "policy": {"research_only": True, "non_gating": True},
        "ok": ok,
        "steps": steps,
        "compare": compare,
        "ms_citation_contract": {
            "allowed_metric": "text_blind_tier_v1_hit_at_1_strict",
            "allowed_value": tb1,
            "tier_v2_must_not_replace_ms_headline": True,
            "baseline_contaminated_by_tier_v2": contaminated,
        },
        "interpretation_ko": (
            "MS/대외 인용은 historical text_blind tier_v1만. "
            "tier_v2는 hardset locked_eval 전용 보정; historical AB로 baseline 오염 여부 분리 보고."
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "compare": compare, "contaminated": contaminated}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
