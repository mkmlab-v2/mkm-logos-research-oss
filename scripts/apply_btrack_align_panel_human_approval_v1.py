#!/usr/bin/env python3
"""Record commander approval and promote align-panel B-track score to operational paths.

Copies pre-validated align-promotion-push-panel artifacts (nbps=2.0, dual strict pass)
to ``btrack_prophecy_score_latest.json`` and recommended-chain latest pointers.
Does NOT enable live trading or Track A promotion.
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
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

SRC_SCORE = REPORTS / "btrack_prophecy_score_recommended_align_panel_nbps2_v1.json"
SRC_LENS = REPORTS / "prophecy_per_date_combo_walkforward_align_panel_nbps2_v1.json"
SRC_INST = REPORTS / "prophecy_instrument_combo_walkforward_align_panel_nbps2_v1.json"
SRC_GATES = REPORTS / "prophecy_promotion_gates_align_panel_nbps2_v1.json"
ABlation = REPORTS / "lens_wf_fold3_and_align_panel_ablation_v1_latest.json"

DEFAULT_APPROVAL = ART / "btrack_align_panel_human_approval_v1_latest.json"
OPER_SCORE = ART / "btrack_prophecy_score_latest.json"
ARCHIVE_SCORE = ART / "btrack_prophecy_score_pre_align_panel_archive_v1_latest.json"
APPLY_SUMMARY = REPORTS / "btrack_align_panel_apply_summary_v1_latest.json"

RPT_SCORE = REPORTS / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
RPT_LENS = REPORTS / "prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
RPT_INST = REPORTS / "prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json"
RPT_GATES = REPORTS / "prophecy_promotion_gates_recommended_chain_v1_latest.json"

ART_GATES = ART / "prophecy_promotion_gates_v1_latest.json"
ART_LENS = ART / "prophecy_per_date_combo_walkforward_v1_latest.json"
ART_INST = ART / "prophecy_instrument_combo_walkforward_v1_latest.json"
OPER_EVAL = ART / "prophecy_hit_rate_eval_latest.json"
DAILY_EVAL = ART / "prophecy_hit_rate_eval_daily_operational_latest.json"
ARCHIVE_EVAL = ART / "prophecy_hit_rate_eval_pre_align_panel_archive_v1_latest.json"


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


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _copy(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise SystemExit(f"missing source: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"COPIED: {_rel(src)} -> {_rel(dst)}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument(
        "--note-ko",
        default=(
            "align-promotion-push-panel nbps=2.0 승인 — dual strict pass; "
            "per-date v1 + srcdir + expanded prior (B-track); live/Track A 자동 승격 없음."
        ),
    )
    ap.add_argument("--approval-out", type=Path, default=DEFAULT_APPROVAL)
    ap.add_argument("--skip-hit-rate", action="store_true")
    args = ap.parse_args(argv)

    gates = _load(SRC_GATES)
    if not gates.get("combined_all_passed"):
        raise SystemExit(
            f"refusing apply: combined_all_passed is not true in {SRC_GATES}"
        )
    if not gates.get("strict_passed"):
        raise SystemExit(f"refusing apply: strict_passed is not true in {SRC_GATES}")

    score_doc = _load(SRC_SCORE)
    neutral_bps = score_doc.get("neutral_bps")

    copies: list[tuple[Path, Path]] = [
        (SRC_SCORE, RPT_SCORE),
        (SRC_LENS, RPT_LENS),
        (SRC_INST, RPT_INST),
        (SRC_GATES, RPT_GATES),
        (SRC_SCORE, OPER_SCORE),
        (SRC_LENS, ART_LENS),
        (SRC_INST, ART_INST),
        (SRC_GATES, ART_GATES),
    ]

    if OPER_SCORE.is_file():
        _copy(OPER_SCORE, ARCHIVE_SCORE)
    if OPER_EVAL.is_file():
        _copy(OPER_EVAL, ARCHIVE_EVAL)

    for src, dst in copies:
        if dst == OPER_SCORE and OPER_SCORE.is_file() and ARCHIVE_SCORE.is_file():
            pass
        _copy(src, dst)

    eval_metrics: dict[str, Any] = {}
    py = sys.executable
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
        "schema": "btrack_align_panel_human_approval_v1",
        "approved_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "decision": "APPROVED_ALIGN_PANEL_OPERATIONAL_SCORE",
        "reviewer": args.reviewer,
        "note_ko": args.note_ko,
        "live_trading_enabled": False,
        "track_a_auto_promote": False,
        "would_change_active": True,
        "neutral_bps": neutral_bps,
        "promotion_config": {
            "align_promotion_push_panel": True,
            "include_source_direction_signal": True,
            "include_expanded_prior_features": True,
            "per_date_direction_json": "reports/per_date_v1_180d.json",
            "recent_trading_days": 180,
        },
        "gate_snapshot": {
            "combined_all_passed": gates.get("combined_all_passed"),
            "strict_passed": gates.get("strict_passed"),
            "strict_pass_streak": gates.get("strict_pass_streak"),
            "outcome_class": gates.get("outcome_class"),
            "lens_mean_test_accuracy": (_load(SRC_LENS).get("aggregate") or {}).get(
                "mean_test_accuracy"
            ),
        },
        "evidence": {
            "gates": _rel(SRC_GATES),
            "score": _rel(SRC_SCORE),
            "lens_wf": _rel(SRC_LENS),
            "instrument_wf": _rel(SRC_INST),
            "ablation": _rel(ABlation) if ABlation.is_file() else None,
        },
        "archives": {
            "score_pre_align_panel": _rel(ARCHIVE_SCORE) if ARCHIVE_SCORE.is_file() else None,
            "eval_pre_align_panel": _rel(ARCHIVE_EVAL) if ARCHIVE_EVAL.is_file() else None,
        },
        "operational_pointers": {
            "score": _rel(OPER_SCORE),
            "eval": _rel(OPER_EVAL),
            "recommended_gates": _rel(RPT_GATES),
        },
        "explicit_hold": {
            "live_trading_auto_enable": False,
            "track_a_auto_merge": False,
            "ms_headline_kpi_update": False,
            "fail_comp_004_active_report": False,
        },
        "operational_headline_metrics": {
            "price_directional_hit_rate": eval_metrics.get("price_directional_hit_rate"),
            "n_evaluated": eval_metrics.get("n_evaluated"),
        },
    }
    args.approval_out.parent.mkdir(parents=True, exist_ok=True)
    args.approval_out.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {_rel(args.approval_out)}")

    summary = {
        "schema": "btrack_align_panel_apply_summary_v1",
        "applied_at_utc": approval["approved_at_utc"],
        "research_only": True,
        "neutral_bps": neutral_bps,
        "combined_all_passed": True,
        "copies": [{"from": _rel(s), "to": _rel(d)} for s, d in copies],
        "approval": _rel(args.approval_out),
        "headline_hit_rate": eval_metrics.get("price_directional_hit_rate"),
    }
    APPLY_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {_rel(APPLY_SUMMARY)}")
    print(
        f"DONE align_panel neutral_bps={neutral_bps} "
        f"headline_hit={eval_metrics.get('price_directional_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
