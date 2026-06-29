#!/usr/bin/env python3
"""Compare text_blind vs rag_assisted era eval on hardset v2 + historical gold ([HYPO])."""
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
DEFAULT_HARDSET_GOLD = ROOT / "docs/final/artifacts/logos_chronology_hardset_news_era_gold_v2_latest.json"
DEFAULT_HIST_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_chronology_rag_assisted_eval_compare_v1_latest.json"


def _run_eval(
    gold: Path,
    tag_mode: str,
    out: Path,
    *,
    boost_policy: str = "tier_v1",
    reval_key: str | None = None,
) -> dict[str, Any]:
    cmd = [
        PY,
        str(ROOT / "scripts/eval_logos_chronology_era_blind_v1.py"),
        "--gold-json",
        str(gold),
        "--tag-mode",
        tag_mode,
        "--modern-boost",
        "0.08",
        "--boost-policy",
        boost_policy,
        "--output-json",
        str(out),
    ]
    if reval_key:
        cmd.extend(
            [
                "--append-revalidation",
                str(ROOT / "docs/final/artifacts/logos_symbolic_revalidation_report_latest.json"),
                "--revalidation-key",
                reval_key,
            ]
        )
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary: dict[str, Any] = {}
    if out.is_file():
        doc = json.loads(out.read_text(encoding="utf-8-sig"))
        summary = dict(doc.get("summary") or {})
        summary["status"] = doc.get("status")
        summary["governance_flags"] = (doc.get("governance") or {}).get("flags")
    return {"exit_code": cp.returncode, "summary": summary, "output_json": str(out.relative_to(ROOT)).replace("\\", "/")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hardset-gold-json", type=Path, default=DEFAULT_HARDSET_GOLD)
    ap.add_argument("--historical-gold-json", type=Path, default=DEFAULT_HIST_GOLD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-historical", action="store_true")
    ap.add_argument(
        "--hardset-boost-policy",
        default="tier_v2_locked_eval",
        choices=("tier_v1", "tier_v2_locked_eval"),
        help="hardset lane only; historical stays tier_v1 (MS baseline 격벽)",
    )
    args = ap.parse_args()

    art = ROOT / "docs/final/artifacts"
    if args.hardset_boost_policy == "tier_v2_locked_eval":
        hardset_tb = art / "logos_chronology_hardset_text_blind_v2_tier_v2_eval_v1_latest.json"
        hardset_rag = art / "logos_chronology_hardset_rag_assisted_v2_tier_v2_eval_v1_latest.json"
    else:
        hardset_tb = art / "logos_chronology_hardset_text_blind_v2_tier_v1_baseline_eval_v1_latest.json"
        hardset_rag = art / "logos_chronology_hardset_rag_assisted_v2_eval_v1_latest.json"
    hist_tb = art / "logos_chronology_era_blind_eval_text_blind_v1_latest.json"
    hist_rag = art / "logos_chronology_era_blind_eval_rag_assisted_v1_latest.json"

    steps: dict[str, Any] = {
        "hardset_text_blind": _run_eval(
            args.hardset_gold_json,
            "text_blind",
            hardset_tb,
            boost_policy=args.hardset_boost_policy,
            reval_key="non_synthetic_era_blind_eval_hardset_v2",
        ),
        "hardset_rag_assisted": _run_eval(
            args.hardset_gold_json,
            "rag_assisted",
            hardset_rag,
            boost_policy=args.hardset_boost_policy,
            reval_key="non_synthetic_era_blind_eval_hardset_v2_rag_assisted",
        ),
    }
    if not args.skip_historical:
        steps["historical_text_blind"] = _run_eval(args.historical_gold_json, "text_blind", hist_tb)
        steps["historical_rag_assisted"] = _run_eval(args.historical_gold_json, "rag_assisted", hist_rag)

    def _delta(a: dict[str, Any], b: dict[str, Any]) -> float | None:
        h1 = (a.get("summary") or {}).get("hit_at_1_strict")
        h2 = (b.get("summary") or {}).get("hit_at_1_strict")
        if h1 is None or h2 is None:
            return None
        return round(float(h2) - float(h1), 6)

    compare = {
        "hardset_hit_at_1_delta_rag_minus_text": _delta(steps["hardset_text_blind"], steps["hardset_rag_assisted"]),
        "hardset_locked_eval_rag": (steps["hardset_rag_assisted"].get("summary") or {}).get(
            "locked_eval_hit_at_1_strict"
        ),
        "hardset_locked_eval_text": (steps["hardset_text_blind"].get("summary") or {}).get(
            "locked_eval_hit_at_1_strict"
        ),
    }
    if not args.skip_historical:
        compare["historical_hit_at_1_delta_rag_minus_text"] = _delta(
            steps["historical_text_blind"], steps["historical_rag_assisted"]
        )

    ok = all(v.get("exit_code") == 0 for v in steps.values())
    doc = {
        "schema": "logos_chronology_rag_assisted_eval_compare_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "policy": {"research_only": True, "non_gating": True},
        "ok": ok,
        "steps": steps,
        "compare": compare,
        "interpretation_ko": (
            "rag_assisted는 text_blind+오프라인 GraphRAG topic enrichment PoC. "
            "MS/대외 인용은 historical text_blind만. B→A·실매매 합선 없음."
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "compare": compare}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
