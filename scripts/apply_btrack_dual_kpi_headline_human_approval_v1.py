#!/usr/bin/env python3
"""Record commander approval: KPI-B per-date WF as operational B-track headline.

Archives current KPI-A frozen score/eval, promotes KPI-B shadow artifacts to operational
pointers (prophecy_hit_rate_eval_latest.json, btrack_prophecy_score_latest.json).

Does NOT enable live trading or Track A auto-promotion.
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
POLICY = ART / "btrack_dual_kpi_headline_policy_v1.json"
DEFAULT_APPROVAL_OUT = ART / "btrack_dual_kpi_headline_human_approval_v1_latest.json"
ARCHIVE_EVAL = ART / "prophecy_hit_rate_eval_kpi_a_frozen_archive_v1_latest.json"
ARCHIVE_SCORE = ART / "btrack_prophecy_score_kpi_a_frozen_archive_v1_latest.json"
OPER_EVAL = ART / "prophecy_hit_rate_eval_latest.json"
OPER_SCORE = ART / "btrack_prophecy_score_latest.json"
SHADOW_EVAL = ART / "prophecy_hit_rate_eval_kpi_b_shadow_v1_latest.json"
SHADOW_SCORE = ART / "btrack_prophecy_score_kpi_b_shadow_v1_latest.json"
SHADOW_SUMMARY = REPORTS / "btrack_kpi_b_shadow_summary_v1_latest.json"
COMPARE = REPORTS / "frozen_vs_per_date_panel_compare_v1_latest.json"


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


def _copy_json(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise SystemExit(f"missing source: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"COPIED: {src.resolve()} -> {dst.resolve()}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note-ko", default="KPI-B per-date WF approved as operational headline (Dual-KPI v1).")
    ap.add_argument("--approval-out", type=Path, default=DEFAULT_APPROVAL_OUT)
    ap.add_argument("--skip-shadow-refresh", action="store_true", help="Do not re-run shadow eval before promote.")
    args = ap.parse_args(argv)

    if not args.skip_shadow_refresh:
        rc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_btrack_kpi_b_shadow_eval_v1.py")],
            cwd=str(ROOT),
        ).returncode
        if rc != 0:
            raise SystemExit(rc)

    if not SHADOW_EVAL.is_file() or not SHADOW_SCORE.is_file():
        raise SystemExit("KPI-B shadow artifacts missing; run run_btrack_kpi_b_shadow_eval_v1.py first")

    if OPER_EVAL.is_file():
        _copy_json(OPER_EVAL, ARCHIVE_EVAL)
    if OPER_SCORE.is_file():
        _copy_json(OPER_SCORE, ARCHIVE_SCORE)

    _copy_json(SHADOW_EVAL, OPER_EVAL)
    _copy_json(SHADOW_SCORE, OPER_SCORE)

    summary = _load(SHADOW_SUMMARY)
    compare = _load(COMPARE)
    oper_eval = _load(OPER_EVAL)
    metrics = oper_eval.get("metrics") if isinstance(oper_eval.get("metrics"), dict) else {}

    approval: dict[str, Any] = {
        "schema": "btrack_dual_kpi_headline_human_approval_v1",
        "approved_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "decision": "APPROVED_KPI_B_OPERATIONAL_HEADLINE",
        "headline_scoring_axis": "kpi_b_per_date_wf",
        "previous_axis": "kpi_a_frozen_single_direction_batch",
        "reviewer": args.reviewer,
        "note_ko": args.note_ko,
        "live_trading_enabled": False,
        "track_a_auto_promote": False,
        "policy_pointer": str(POLICY.relative_to(ROOT)),
        "archives": {
            "kpi_a_eval": str(ARCHIVE_EVAL.relative_to(ROOT)),
            "kpi_a_score": str(ARCHIVE_SCORE.relative_to(ROOT)),
        },
        "operational_pointers": {
            "eval": str(OPER_EVAL.relative_to(ROOT)),
            "score": str(OPER_SCORE.relative_to(ROOT)),
        },
        "operational_headline_metrics": {
            "price_directional_hit_rate": metrics.get("price_directional_hit_rate"),
            "n_evaluated": metrics.get("n_evaluated"),
            "scoring_mode": metrics.get("scoring_mode"),
        },
        "kpi_b_shadow_summary": summary.get("kpi_b"),
        "delta_b_minus_a_at_approval": summary.get("delta_b_minus_a"),
        "dual_kpi_compare_pointer": str(COMPARE.relative_to(ROOT)) if compare else None,
    }
    args.approval_out.parent.mkdir(parents=True, exist_ok=True)
    args.approval_out.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.approval_out.resolve()}")
    print(
        f"OPERATIONAL headline: {metrics.get('price_directional_hit_rate')} "
        f"(n={metrics.get('n_evaluated')}) mode={metrics.get('scoring_mode')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
