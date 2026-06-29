#!/usr/bin/env python3
"""[HYPO] Mission C shadow: 180d per-date + bull_reversal_flow + srcdir/expanded WF.

Writes reports/* only — never overwrites docs/final operational score/headline KPI.
Appends strict-pass streak to a dedicated Mission C history file.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_btrack_prophecy_score_from_ohlcv.py"
WF = ROOT / "scripts" / "run_prophecy_per_date_combo_walkforward_v1.py"
GATES = ROOT / "scripts" / "eval_prophecy_promotion_gates_v1.py"
PER_DATE_BUILD = ROOT / "scripts" / "build_btrack_ensemble_per_date_directions_v1.py"
OPS_STATUS = ROOT / "scripts" / "build_mission_c_shadow_ops_status_v1.py"
PASSIVE_ALERTS = ROOT / "scripts" / "check_mission_c_shadow_passive_alerts_v1.py"

DEFAULT_PER_DATE = ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"

DEFAULT_SCORE_OUT = ROOT / "reports/btrack_prophecy_score_mission_c_shadow_v1_latest.json"
DEFAULT_WF_OUT = ROOT / "reports/mission_c_shadow_wf_srcdir_expanded_v1_latest.json"
DEFAULT_GATES_OUT = ROOT / "reports/prophecy_promotion_gates_mission_c_shadow_v1_latest.json"
DEFAULT_STREAK = ROOT / "reports/prophecy_promotion_strict_streak_mission_c_shadow_v1.json"
DEFAULT_SUMMARY = ROOT / "reports/mission_c_srcdir_expanded_shadow_summary_v1_latest.json"
DEFAULT_LOG_JSONL = ROOT / "reports/mission_c_srcdir_expanded_shadow_log.jsonl"
DEFAULT_BRIEFING = ROOT / "reports/mission_c_srcdir_expanded_briefing_v1_latest.md"

SCHEMA_SUMMARY = "mission_c_srcdir_expanded_shadow_summary_v1"
CALIBRATION_NOTE = "mission_c_shadow_v1:180d+bull_reversal_flow+srcdir_expanded;reports_only"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def _wf_agg(wf_path: Path) -> dict[str, Any]:
    doc = _load_json(wf_path) or {}
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    return {
        "mean_test_accuracy": agg.get("mean_test_accuracy"),
        "stdev_test_accuracy": agg.get("stdev_test_accuracy"),
        "min_test_accuracy": agg.get("min_test_accuracy"),
        "fraction_test_beats_always_bull": agg.get("fraction_test_beats_always_bull"),
    }


def _write_briefing(
    path: Path,
    *,
    gates: dict[str, Any],
    wf: dict[str, Any],
    streak: int,
    streak_required: int,
) -> None:
    outcome = str(gates.get("outcome_class") or "unknown")
    strict = bool(gates.get("strict_passed"))
    mean = wf.get("mean_test_accuracy")
    stdev = wf.get("stdev_test_accuracy")
    mean_s = f"{float(mean) * 100:.1f}%" if isinstance(mean, (int, float)) else "n/a"
    stdev_s = f"{float(stdev) * 100:.2f}%" if isinstance(stdev, (int, float)) else "n/a"
    lines = [
        "# Mission C shadow briefing (operator · 5 lines)",
        "",
        f"1. **연습장 로봇** — 180일 공부 + 안정 시험(mean {mean_s}, 기복 {stdev_s}); 판정 `{outcome}` · strict={'PASS' if strict else 'FAIL'}.",
        f"2. **실전 금지** — `research_only` · Track A/live 합선 없음 · streak **{streak}/{streak_required}**.",
        "3. **30일 벼락치기 금지** — WF 안정성은 180일 채점 기준만 신뢰.",
        "4. **본선 미변경** — `btrack_prophecy_score_latest.json` 등 operational SSOT overwrite 없음.",
        f"5. **다음** — 패시브 감시만; streak {streak_required} 연속 strict 전까지 human apply 검토 금지.",
        "",
        f"_generated_at_utc: {_utc_now()}_",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPO)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--strict-streak-required", type=int, default=5)
    ap.add_argument("--skip-per-date-rebuild", action="store_true")
    ap.add_argument("--score-out", type=Path, default=DEFAULT_SCORE_OUT)
    ap.add_argument("--wf-out", type=Path, default=DEFAULT_WF_OUT)
    ap.add_argument("--gates-out", type=Path, default=DEFAULT_GATES_OUT)
    ap.add_argument("--streak-history-json", type=Path, default=DEFAULT_STREAK)
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG_JSONL)
    ap.add_argument("--briefing-out", type=Path, default=DEFAULT_BRIEFING)
    ap.add_argument("--skip-perception-plane", action="store_true")
    args = ap.parse_args(argv)

    if not args.skip_per_date_rebuild or not args.per_date_json.is_file():
        rc = _run(
            [
                sys.executable,
                str(PER_DATE_BUILD),
                "--output",
                str(args.per_date_json),
                "--recent-trading-days",
                str(args.recent_trading_days),
            ]
        )
        if rc != 0:
            return rc

    if not args.btc_csv.is_file():
        print(f"missing btc csv: {args.btc_csv}", file=sys.stderr)
        return 2

    score_cmd = [
        sys.executable,
        str(BUILD),
        "--recent-trading-days",
        str(args.recent_trading_days),
        "--force-dual-leg-panel",
        "--btc-csv",
        str(args.btc_csv),
        "--per-date-direction-json",
        str(args.per_date_json),
        "--bull-reversal-lookback",
        "3",
        "--bull-reversal-threshold-pct",
        "6",
        "--bull-reversal-target",
        "neutral",
        "--bull-reversal-require-flow",
        "--bull-reversal-min-flow-score",
        "1000",
        "--output",
        str(args.score_out),
    ]
    if args.kospi_csv.is_file():
        score_cmd.extend(["--kospi-csv", str(args.kospi_csv)])
    if rc := _run(score_cmd):
        return rc

    wf_cmd = [
        sys.executable,
        str(WF),
        "--score-json",
        str(args.score_out),
        "--btc-csv",
        str(args.btc_csv),
        "--n-folds",
        str(args.n_folds),
        "--target-instrument",
        "btc",
        "--train-objective",
        "margin_vs_bull",
        "--include-source-direction-signal",
        "--include-expanded-prior-features",
        "--output",
        str(args.wf_out),
    ]
    if args.kospi_csv.is_file():
        wf_cmd.extend(["--kospi-csv", str(args.kospi_csv)])
    if rc := _run(wf_cmd):
        return rc

    gates_cmd = [
        sys.executable,
        str(GATES),
        "--promotion-track-mode",
        "btc_only_crossassist",
        "--lens-walkforward-json",
        str(args.wf_out),
        "--score-json",
        str(args.score_out),
        "--hypothesis-json",
        str(args.hypothesis_json),
        "--streak-history-json",
        str(args.streak_history_json),
        "--strict-streak-required",
        str(args.strict_streak_required),
        "--calibration-note",
        CALIBRATION_NOTE,
        "--output",
        str(args.gates_out),
    ]
    if rc := _run(gates_cmd):
        return rc

    gates_doc = _load_json(args.gates_out) or {}
    wf_metrics = _wf_agg(args.wf_out)
    streak = int(gates_doc.get("strict_pass_streak") or 0)
    strict_passed = bool(gates_doc.get("strict_passed"))

    summary = {
        "schema": SCHEMA_SUMMARY,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "boundary_ack": "Shadow only; no operational headline or Track A/live merge.",
        "recipe_id": "mission_c_srcdir_expanded_v1",
        "inputs": {
            "per_date_json": _rel(args.per_date_json),
            "score_json": _rel(args.score_out),
            "wf_json": _rel(args.wf_out),
            "gates_json": _rel(args.gates_out),
            "streak_history_json": _rel(args.streak_history_json),
            "recent_trading_days": args.recent_trading_days,
            "n_folds": args.n_folds,
        },
        "wf_aggregate": wf_metrics,
        "gates": {
            "strict_passed": strict_passed,
            "combined_all_passed": gates_doc.get("combined_all_passed"),
            "outcome_class": gates_doc.get("outcome_class"),
            "promotion_recommendation": gates_doc.get("promotion_recommendation"),
            "strict_pass_streak": streak,
            "strict_streak_required": args.strict_streak_required,
            "auto_promote_ready": gates_doc.get("auto_promote_ready"),
        },
        "reproducible_command": (
            "py scripts/run_mission_c_srcdir_expanded_shadow_v1.py"
        ),
    }
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_row = {
        "ts_utc": _utc_now(),
        "strict_passed": strict_passed,
        "outcome_class": gates_doc.get("outcome_class"),
        "strict_pass_streak": streak,
        "mean_test_accuracy": wf_metrics.get("mean_test_accuracy"),
        "stdev_test_accuracy": wf_metrics.get("stdev_test_accuracy"),
    }
    args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.log_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_row, ensure_ascii=False) + "\n")

    _write_briefing(
        args.briefing_out,
        gates=gates_doc,
        wf=wf_metrics,
        streak=streak,
        streak_required=args.strict_streak_required,
    )

    if not args.skip_perception_plane:
        for extra_cmd in (
            [sys.executable, str(OPS_STATUS)],
            [sys.executable, str(PASSIVE_ALERTS), "--skip-webhook", "--skip-telegram"],
        ):
            if rc := _run(extra_cmd):
                print(f"WARN: perception plane step failed exit {rc}: {' '.join(extra_cmd)}", file=sys.stderr)

    print(
        f"WROTE: {args.summary_out.resolve()} "
        f"outcome={gates_doc.get('outcome_class')} streak={streak}/{args.strict_streak_required}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
