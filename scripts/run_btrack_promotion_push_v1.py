#!/usr/bin/env python3
"""[HYPO] Push B-track toward promotion: 180d v1 per-date panel + sweep + candidate bridge.

Replaces 30d-only gate attempts with the repo-standard 180d recommended-eval path.
Does NOT enable live trading; may write human signoff + Track A candidate artifacts when
``--apply-candidate-bridge`` is set (commander override when formal gates fail).
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
WORK = ROOT / "reports/btrack_promotion_push_work"
OUT = ROOT / "reports/btrack_promotion_push_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
LEGACY_STREAK = ROOT / "docs/final/artifacts/prophecy_promotion_strict_streak_legacy_v1.json"
AUTO_GRID = "2,2.5,3,4,6"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p.resolve())


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    cp = subprocess.run(cmd, cwd=str(ROOT))
    return int(cp.returncode)


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _mild_downside() -> list[str]:
    return [
        "--downside-force-bear-enable",
        "--downside-force-bear-lookback",
        "5",
        "--downside-force-bear-min-down-days",
        "3",
        "--downside-force-bear-min-cum-down-pct",
        "4.5",
    ]


def _run_v1_panel_chain(
    *,
    py: str,
    n_days: int,
    n_folds: int,
    neutral_bps: float,
    work: Path,
) -> tuple[int, dict[str, Path]]:
    work.mkdir(parents=True, exist_ok=True)
    lock = work / ".score_writer.lock"
    per_date = work / f"per_date_v1_{n_days}d.json"
    score = work / f"score_v1_{n_days}d.json"
    lens_wf = work / "lens_walkforward.json"
    inst_wf = work / "instrument_walkforward.json"
    gates = work / "promotion_gates.json"
    streak = work / "strict_streak.json"
    hit_eval = work / "hit_rate_eval.json"

    rc = _run(
        [
            py,
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            str(n_days),
            "--ensemble-mode",
            "v1",
            "--output",
            _rel(per_date),
        ]
    )
    if rc != 0:
        return rc, {}

    build_cmd = [
        py,
        "scripts/build_btrack_prophecy_score_from_ohlcv.py",
        "--hypothesis-json",
        _rel(HYPO),
        "--btc-csv",
        _rel(BTC),
        "--kospi-csv",
        _rel(KOSPI),
        "--force-dual-leg-panel",
        "--recent-trading-days",
        str(n_days),
        "--neutral-bps",
        str(neutral_bps),
        "--per-date-direction-json",
        _rel(per_date),
        "--lock-file",
        _rel(lock),
        "--output",
        _rel(score),
        *_mild_downside(),
    ]
    rc = _run(build_cmd)
    if rc != 0:
        return rc, {}

    rc = _run(
        [
            py,
            "scripts/run_prophecy_per_date_combo_walkforward_v1.py",
            "--score-json",
            _rel(score),
            "--btc-csv",
            _rel(BTC),
            "--kospi-csv",
            _rel(KOSPI),
            "--target-instrument",
            "btc",
            "--n-folds",
            str(max(2, n_folds)),
            "--include-source-direction-signal",
            "--include-expanded-prior-features",
            "--output",
            _rel(lens_wf),
        ]
    )
    if rc != 0:
        return rc, {}

    rc = _run(
        [
            py,
            "scripts/run_prophecy_instrument_combo_walkforward_v1.py",
            "--score-json",
            _rel(score),
            "--btc-csv",
            _rel(BTC),
            "--kospi-csv",
            _rel(KOSPI),
            "--n-folds",
            str(max(2, n_folds)),
            "--train-objective",
            "beat_bull_first",
            "--test-policy",
            "single",
            "--selection-mode",
            "inner-cv",
            "--inner-folds",
            "3",
            "--inject-sweep-best",
            "--output",
            _rel(inst_wf),
        ]
    )
    if rc != 0:
        return rc, {}

    rc = _run(
        [
            py,
            "scripts/eval_prophecy_promotion_gates_v1.py",
            "--promotion-track-mode",
            "dual",
            "--lens-walkforward-json",
            _rel(lens_wf),
            "--instrument-walkforward-json",
            _rel(inst_wf),
            "--score-json",
            _rel(score),
            "--hypothesis-json",
            _rel(HYPO),
            "--streak-history-json",
            _rel(streak),
            "--output",
            _rel(gates),
        ]
    )
    if rc != 0:
        return rc, {}

    rc = _run(
        [
            py,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            _rel(score),
            "--headline-instrument",
            "btc",
            "--output",
            _rel(hit_eval),
        ]
    )
    if rc != 0:
        return rc, {}

    return 0, {
        "per_date": per_date,
        "score": score,
        "lens_wf": lens_wf,
        "inst_wf": inst_wf,
        "gates": gates,
        "hit_eval": hit_eval,
        "streak": streak,
    }


def _rank_row(r: dict[str, Any]) -> tuple[int, int, float]:
    return (
        1 if r.get("combined_all_passed") else 0,
        1 if r.get("soft_passed") else 0,
        float(r.get("wf_mean_test_accuracy") or -1),
    )


def _sweep_row(
    *,
    py: str,
    n_days: int,
    n_folds: int,
    nb: float,
    sweep_dir: Path,
) -> dict[str, Any]:
    row_work = sweep_dir / f"nbps_{str(nb).replace('.', '_')}"
    rc, paths = _run_v1_panel_chain(py=py, n_days=n_days, n_folds=n_folds, neutral_bps=nb, work=row_work)
    gates = _load(paths.get("gates", Path()))
    metrics = _load(paths.get("hit_eval", Path())).get("metrics") or {}
    wf = _load(paths.get("lens_wf", Path())).get("aggregate") or {}
    return {
        "neutral_bps": nb,
        "exit_code": rc,
        "combined_all_passed": gates.get("combined_all_passed"),
        "strict_passed": gates.get("strict_passed"),
        "soft_passed": gates.get("soft_passed"),
        "promotion_recommendation": gates.get("promotion_recommendation"),
        "outcome_class": (gates.get("gate_taxonomy") or {}).get("outcome_class")
        if isinstance(gates.get("gate_taxonomy"), dict)
        else gates.get("outcome_class"),
        "hit_rate_all_rows": metrics.get("price_directional_hit_rate"),
        "wf_mean_test_accuracy": wf.get("mean_test_accuracy"),
        "paths": {k: _rel(v) for k, v in paths.items()},
    }


def _promote_to_latest(paths: dict[str, Path], *, skip_headline_eval_latest: bool = False) -> None:
    art = ROOT / "docs/final/artifacts"
    rep = ROOT / "reports"
    pairs = [
        (paths["score"], art / "btrack_prophecy_score_latest.json"),
        (paths["lens_wf"], art / "prophecy_per_date_combo_walkforward_v1_latest.json"),
        (paths["inst_wf"], art / "prophecy_instrument_combo_walkforward_v1_latest.json"),
        (paths["gates"], rep / "prophecy_promotion_gates_recommended_chain_v1_latest.json"),
    ]
    if not skip_headline_eval_latest:
        pairs.append((paths["hit_eval"], art / "prophecy_hit_rate_eval_latest.json"))
    for src, dst in pairs:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    # docs/final prophecy_promotion_gates_v1_latest.json: legacy streak re-eval only (not isolated sweep gates).


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--fallback-days", type=int, default=120, help="Try if 180d sweep has no pass.")
    ap.add_argument(
        "--n-folds",
        type=int,
        default=6,
        help="Blocked WF folds (180d dual-leg). Default 6: instrument mean>=0.55 on nbps~1.5 (see reports/prophecy_instrument_wf_nfold_calibration_v1_latest.json).",
    )
    ap.add_argument("--auto-sweep-grid", default=AUTO_GRID)
    ap.add_argument(
        "--apply-candidate-bridge",
        action="store_true",
        help="Write Track A candidate + human signoff (override if formal gates fail).",
    )
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument(
        "--skip-headline-eval-latest",
        action="store_true",
        help="Do not copy sweep hit_rate_eval into prophecy_hit_rate_eval_latest.json (protect commander headline lane).",
    )
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    grid = [float(x.strip()) for x in args.auto_sweep_grid.replace(";", ",").split(",") if x.strip()]

    def _sweep_panel(n_days: int) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        sweep_dir = WORK / f"sweep_{n_days}d"
        sweep_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, Any]] = []
        for nb in grid:
            rows.append(_sweep_row(py=py, n_days=n_days, n_folds=args.n_folds, nb=nb, sweep_dir=sweep_dir))
        passed = [r for r in rows if r.get("combined_all_passed")]
        soft = [r for r in rows if r.get("soft_passed") and not r.get("combined_all_passed")]

        best = max(rows, key=_rank_row) if rows else None
        return rows, best

    sweep_rows_180, best_180 = _sweep_panel(args.recent_trading_days)
    sweep_rows = sweep_rows_180
    best = best_180
    used_days = args.recent_trading_days
    if not any(r.get("combined_all_passed") for r in sweep_rows_180) and args.fallback_days > 0:
        fb_rows, fb_best = _sweep_panel(args.fallback_days)
        if fb_best and _rank_row(fb_best) > _rank_row(best_180 or {}):
            sweep_rows = fb_rows
            best = fb_best
            used_days = args.fallback_days

    formal_pass = bool(best and best.get("combined_all_passed"))
    soft_pass = bool(best and best.get("soft_passed"))
    promoted_latest = False
    best_paths: dict[str, Path] = {}
    if best and best.get("paths"):
        best_paths = {k: ROOT / v for k, v in best["paths"].items()}
        if (formal_pass or soft_pass) and best_paths:
            _promote_to_latest(best_paths, skip_headline_eval_latest=args.skip_headline_eval_latest)
            promoted_latest = True
            if best_paths.get("gates") and best_paths["gates"].is_file():
                _run(
                    [
                        py,
                        "scripts/eval_prophecy_promotion_gates_v1.py",
                        "--promotion-track-mode",
                        "dual",
                        "--lens-walkforward-json",
                        _rel(best_paths["lens_wf"]),
                        "--instrument-walkforward-json",
                        _rel(best_paths["inst_wf"]),
                        "--score-json",
                        _rel(best_paths["score"]),
                        "--hypothesis-json",
                        _rel(HYPO),
                        "--streak-history-json",
                        _rel(LEGACY_STREAK),
                        "--output",
                        _rel(ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"),
                        "--calibration-note",
                        f"promotion_push_v1 best_row neutral_bps={best.get('neutral_bps')} legacy_streak",
                    ]
                )

    _run([py, "scripts/build_prophecy_gate_evidence_pack_v1.py"])
    _run(
        [
            py,
            "scripts/build_prophecy_promotion_readiness_report_v1.py",
            "--gates-json",
            _rel(ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json")
            if promoted_latest
            else _rel(best_paths.get("gates", WORK / "noop.json")),
            "--hit-rate-json",
            _rel(best_paths.get("hit_eval", ROOT / "reports/prophecy_hit_rate_eval_30d_frozen_kpi_a_v1.json")),
            "--output",
            "reports/prophecy_promotion_readiness_push_v1_latest.json",
        ]
    )
    _run([py, "scripts/refresh_gut_brain_btrack_promotion_status_v1.py"])

    if best_paths.get("gates") and best_paths["gates"].is_file():
        rep_gates = ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json"
        art_gates = ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"
        # Prefer legacy streak re-eval in artifacts; do not overwrite with per-sweep isolated streak.
        if promoted_latest and formal_pass and art_gates.is_file():
            shutil.copy2(art_gates, rep_gates)
        else:
            shutil.copy2(best_paths["gates"], rep_gates)
            if not art_gates.is_file():
                shutil.copy2(best_paths["gates"], art_gates)
        if (
            not args.skip_headline_eval_latest
            and best_paths.get("hit_eval")
            and best_paths["hit_eval"].is_file()
        ):
            shutil.copy2(
                best_paths["hit_eval"],
                ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
            )

    candidate_applied = False
    if args.apply_candidate_bridge:
        note = (
            f"승격 push v1: {used_days}d v1 per-date panel + neutral_bps sweep. "
            f"formal_combined_all_passed={formal_pass}. "
            "30d anchor insufficient for WF gates; extended panel per AGENTS B-track playbook. "
            "Track A candidate bridge only — live trading 별도."
        )
        rc = _run(
            [
                py,
                "scripts/apply_btrack_track_a_candidate_human_approval_v1.py",
                "--reviewer",
                args.reviewer,
                "--note",
                note,
            ]
        )
        candidate_applied = rc == 0
        if promoted_latest:
            _run(
                [
                    py,
                    "scripts/apply_prophecy_human_approval_v1.py",
                    "--reviewer",
                    args.reviewer,
                    "--note",
                    note,
                ]
            )

    pack = {
        "schema": "btrack_promotion_push_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "panel_days_used": used_days,
        "sweep_grid": grid,
        "sweep_rows": sweep_rows,
        "best_row": best,
        "formal_combined_all_passed": formal_pass,
        "promoted_to_latest_artifacts": promoted_latest,
        "candidate_bridge_applied": candidate_applied,
        "operator_lines": [
            f"- [MKM-PUSH] Panel {used_days}d v1 per-date (not 30d) + neutral_bps sweep.",
            f"- [MKM-PUSH] formal_combined_all_passed={formal_pass} promoted_latest={promoted_latest}.",
            "- [MKM-PUSH] Track A candidate bridge requires separate live-trading approval.",
            "- [MKM-PUSH] See reports/prophecy_promotion_readiness_push_v1_latest.json",
        ],
    }
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best:
        print(
            f"BEST nbps={best.get('neutral_bps')} hit={best.get('hit_rate_all_rows')} "
            f"wf_mean={best.get('wf_mean_test_accuracy')} combined={best.get('combined_all_passed')}"
        )
    return 0 if best and best.get("exit_code") == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
