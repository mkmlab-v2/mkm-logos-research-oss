#!/usr/bin/env python3
"""Record commander approval and promote Type-A BTC guard shadow to operational score.

Archives pre-approval score, promotes guard shadow to btrack_prophecy_score_latest.json,
re-runs hit-rate eval. Does NOT enable live trading.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
REPORTS = ROOT / "reports"
POLICY = ART / "btrack_btc_typea_guard_v1.json"
DEFAULT_APPROVAL = ART / "btrack_btc_typea_guard_human_approval_v1_latest.json"
OPER_SCORE = ART / "btrack_prophecy_score_latest.json"
ARCHIVE_SCORE = ART / "btrack_prophecy_score_pre_typea_guard_archive_v1_latest.json"
SHADOW_SCORE = ART / "btrack_prophecy_score_btc_typea_guard_v1_latest.json"
APPLY_SUMMARY = REPORTS / "btrack_btc_typea_guard_apply_summary_v1_latest.json"
OPER_EVAL = ART / "prophecy_hit_rate_eval_latest.json"
ARCHIVE_EVAL = ART / "prophecy_hit_rate_eval_pre_typea_guard_archive_v1_latest.json"
DAILY_EVAL = ART / "prophecy_hit_rate_eval_daily_operational_latest.json"
MARGIN_GATE = REPORTS / "btrack_btc_margin_walkforward_gate_v1_latest.json"
DECISION_PACK = ART / "btrack_btc_promotion_decision_pack_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _copy(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise SystemExit(f"missing: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"COPIED: {src} -> {dst}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument(
        "--note-ko",
        default="Type-A BTC guard (score_lt=0.12, kospi bull) 승인 — global 60/40 OOS +2.8pp.",
    )
    ap.add_argument("--approval-out", type=Path, default=DEFAULT_APPROVAL)
    ap.add_argument("--skip-hit-rate", action="store_true")
    args = ap.parse_args(argv)

    py = sys.executable
    rc = subprocess.run(
        [py, str(ROOT / "scripts/apply_btrack_btc_typea_guard_to_score_v1.py")],
        cwd=str(ROOT),
    ).returncode
    if rc != 0:
        raise SystemExit(rc)

    if not SHADOW_SCORE.is_file():
        raise SystemExit(f"shadow score missing: {SHADOW_SCORE}")

    summary = _load(APPLY_SUMMARY)
    margin = _load(MARGIN_GATE)
    global_best = (margin.get("global_holdout") or {}).get("best") or {}

    if OPER_SCORE.is_file():
        _copy(OPER_SCORE, ARCHIVE_SCORE)
    if OPER_EVAL.is_file():
        _copy(OPER_EVAL, ARCHIVE_EVAL)

    _copy(SHADOW_SCORE, OPER_SCORE)

    eval_metrics: dict[str, Any] = {}
    if not args.skip_hit_rate:
        rc = subprocess.run(
            [
                py,
                "scripts/eval_prophecy_hit_rate_v1.py",
                "--run-mode",
                "price",
                "--score-json",
                str(OPER_SCORE),
                "--headline-instrument",
                "btc",
                "--allow-headline-write",
                "--output",
                str(DAILY_EVAL),
            ],
            cwd=str(ROOT),
        ).returncode
        if rc != 0:
            raise SystemExit(rc)
        _copy(DAILY_EVAL, OPER_EVAL)
        eval_doc = _load(OPER_EVAL)
        eval_metrics = eval_doc.get("metrics") if isinstance(eval_doc.get("metrics"), dict) else {}

    approval: dict[str, Any] = {
        "schema": "btrack_btc_typea_guard_human_approval_v1",
        "approved_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "decision": "APPROVED_BTC_TYPEA_GUARD_OPERATIONAL_SCORE",
        "reviewer": args.reviewer,
        "note_ko": args.note_ko,
        "live_trading_enabled": False,
        "track_a_auto_promote": False,
        "would_change_active": True,
        "combined_all_passed": False,
        "policy_pointer": str(POLICY.relative_to(ROOT)),
        "evidence": {
            "margin_walkforward_gate": str(MARGIN_GATE.relative_to(ROOT)),
            "global_holdout_test_delta_oos": global_best.get("test_delta_oos"),
            "apply_summary": str(APPLY_SUMMARY.relative_to(ROOT)),
        },
        "archives": {
            "score_pre_guard": str(ARCHIVE_SCORE.relative_to(ROOT)),
            "eval_pre_guard": str(ARCHIVE_EVAL.relative_to(ROOT)) if ARCHIVE_EVAL.is_file() else None,
        },
        "operational_pointers": {
            "score": str(OPER_SCORE.relative_to(ROOT)),
            "eval": str(OPER_EVAL.relative_to(ROOT)),
        },
        "guard_apply_summary": {
            "delta_hit_rate_btc_15d": summary.get("delta_hit_rate"),
            "n_btc_rows_changed": summary.get("n_changes"),
            "baseline_btc_hit_rate": (summary.get("baseline_btc") or {}).get("price_directional_hit_rate"),
            "counterfactual_btc_hit_rate": (summary.get("counterfactual_btc") or {}).get(
                "price_directional_hit_rate"
            ),
        },
        "operational_headline_metrics": {
            "price_directional_hit_rate": eval_metrics.get("price_directional_hit_rate"),
            "n_evaluated": eval_metrics.get("n_evaluated"),
            "headline_instrument": eval_metrics.get("headline_instrument"),
        },
    }
    args.approval_out.parent.mkdir(parents=True, exist_ok=True)
    args.approval_out.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.approval_out.resolve()}")

    pack = _load(DECISION_PACK)
    pack.update(
        {
            "generated_at_utc": _now(),
            "final_action": "APPROVED_SHADOW_TO_OPERATIONAL",
            "promotion_recommendation": "approved_human_signoff",
            "would_change_active": True,
            "human_signoff": {
                "reviewer": args.reviewer,
                "approved_at_utc": approval["approved_at_utc"],
                "artifact": str(args.approval_out.relative_to(ROOT)),
            },
            "operational_promoted": True,
        }
    )
    DECISION_PACK.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"UPDATED: {DECISION_PACK.resolve()}")
    print(
        f"DONE btc_15d_delta={summary.get('delta_hit_rate')} "
        f"headline_hit={eval_metrics.get('price_directional_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
