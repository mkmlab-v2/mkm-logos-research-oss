#!/usr/bin/env python3
"""RQ-028 P6: holdout-based governor knob promotion gate ([HYPO], research_only).

Mechanical pass → WATCH_CONTINUE only. Track A / live trading auto-merge never.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPLAY = ROOT / "reports/a_code_governor_knob_multiday_replay_v1_latest.json"
DEFAULT_THRESHOLDS = (
    ROOT / "experiments/a_code_12ai_v2/specs/a_code_governor_promotion_gate_thresholds_v1.json"
)
DEFAULT_OUT = ROOT / "reports/a_code_governor_promotion_gate_v1_latest.json"

FORBIDDEN_KEYS = frozenset(
    {
        "price_directional_hit_rate",
        "jaccard",
        "saving_pct",
        "live_trading",
        "dual_axis_beat",
        "alignment_pass_rate",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


def _assert_no_forbidden(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden key: {path}.{key}")
            _assert_no_forbidden(value, f"{path}.{key}" if path else key)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_forbidden(item, f"{path}[{i}]")


def _add_check(
    checks: list[dict[str, Any]],
    *,
    check_id: str,
    actual: Any,
    op: str,
    threshold: Any,
    ok: bool | None = None,
    reason: str = "",
) -> None:
    if ok is None:
        if actual is None:
            ok = False
            reason = reason or "missing_metric"
        elif op == ">=":
            ok = float(actual) >= float(threshold)
        elif op == "<=":
            ok = float(actual) <= float(threshold)
        elif op == "==":
            ok = actual == threshold
        else:
            raise ValueError(f"unsupported op: {op}")
    checks.append(
        {
            "id": check_id,
            "status": "PASS" if ok else "FAIL",
            "actual": actual,
            "operator": op,
            "threshold": threshold,
            "reason": reason or None,
        }
    )


def evaluate_gate(
    replay: dict[str, Any],
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    _assert_no_forbidden(replay)

    checks: list[dict[str, Any]] = []
    eval_axes = replay.get("eval_axes") or {}
    orch = eval_axes.get("orchestration_consistency") or {}
    holdout_dates = replay.get("holdout_dates") or []
    n_days = int(replay.get("n_session_days") or 0)

    train_cons = _num(orch.get("train"))
    hold_cons = _num(orch.get("holdout"))
    on_train = (eval_axes.get("governor_knob_delta") or {}).get("pathology_on_train") or {}
    on_holdout = (eval_axes.get("governor_knob_delta") or {}).get("pathology_on_holdout") or {}
    train_lam = _num(on_train.get("mean_token_budget_lambda"))
    hold_lam = _num(on_holdout.get("mean_token_budget_lambda"))
    lam_drift = abs(hold_lam - train_lam) if hold_lam is not None and train_lam is not None else None

    _add_check(
        checks,
        check_id="schema_replay",
        actual=replay.get("schema"),
        op="==",
        threshold="a_code_governor_knob_multiday_replay_v1",
    )
    _add_check(
        checks,
        check_id="rq_id",
        actual=replay.get("rq_id"),
        op="==",
        threshold="RQ-028",
    )
    _add_check(
        checks,
        check_id="research_only_flag",
        actual=replay.get("research_only"),
        op="==",
        threshold=True,
    )
    _add_check(
        checks,
        check_id="min_session_days",
        actual=n_days,
        op=">=",
        threshold=int(thresholds.get("min_session_days", 10)),
    )
    _add_check(
        checks,
        check_id="min_holdout_days",
        actual=len(holdout_dates),
        op=">=",
        threshold=int(thresholds.get("min_holdout_days", 3)),
    )
    _add_check(
        checks,
        check_id="orchestration_consistency_train",
        actual=train_cons,
        op=">=",
        threshold=float(thresholds.get("min_orchestration_consistency_train", 1.0)),
    )
    _add_check(
        checks,
        check_id="orchestration_consistency_holdout",
        actual=hold_cons,
        op=">=",
        threshold=float(thresholds.get("min_orchestration_consistency_holdout", 1.0)),
    )
    _add_check(
        checks,
        check_id="holdout_lambda_drift_vs_train",
        actual=lam_drift,
        op="<=",
        threshold=float(thresholds.get("max_holdout_lambda_drift_vs_train", 0.05)),
    )

    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    total = len(checks)
    all_pass = pass_count == total
    decision = "WATCH_CONTINUE" if all_pass else "HOLD_RESEARCH"

    return {
        "schema": "a_code_governor_promotion_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-028",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "human_sign_off_required": bool(thresholds.get("human_sign_off_required", True)),
        "track_a_auto_promotion": False,
        "live_trading_auto_trigger": False,
        "replay_path": str(DEFAULT_REPLAY.relative_to(ROOT)).replace("\\", "/"),
        "thresholds_path": str(DEFAULT_THRESHOLDS.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            "pass_count": pass_count,
            "total": total,
            "decision": decision,
            "outcome_class": "watch_candidate" if all_pass else "reject",
        },
        "checks": checks,
        "evidence": {
            "n_session_days": n_days,
            "n_holdout_days": len(holdout_dates),
            "orchestration_consistency_train": train_cons,
            "orchestration_consistency_holdout": hold_cons,
            "mean_token_budget_lambda_train": train_lam,
            "mean_token_budget_lambda_holdout": hold_lam,
            "holdout_lambda_drift": lam_drift,
            "pathology_on_vs_off_mean_cap_delta": (replay.get("ablation_summary") or {}).get(
                "pathology_on_vs_off_mean_cap_delta"
            ),
        },
        "track_wall": {
            "track_a_trading": "no_auto_promotion",
            "live_trading_gate": "no_trigger",
            "note_ko": "기계 통과=WATCH_CONTINUE 관측만. 별 RQ·human sign-off 없이 승격 금지.",
        },
        "note_ko": "RQ-028 governor knob holdout gate. 가격·압축·실매매 KPI와 분리.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="A-code governor promotion gate (research_only)")
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--strict", action="store_true", help="exit 1 when decision != WATCH_CONTINUE")
    args = parser.parse_args()

    if not args.replay.is_file():
        print(f"MISSING replay: {args.replay}", flush=True)
        return 2 if args.strict else 0
    if not args.thresholds.is_file():
        raise SystemExit(f"missing thresholds: {args.thresholds}")

    replay = _load(args.replay)
    thresholds = _load(args.thresholds)
    report = evaluate_gate(replay, thresholds)
    report["replay_path"] = str(args.replay.relative_to(ROOT)).replace("\\", "/")
    report["thresholds_path"] = str(args.thresholds.relative_to(ROOT)).replace("\\", "/")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    decision = report["summary"]["decision"]
    print(f"OK: {args.out} decision={decision} pass={report['summary']['pass_count']}/{report['summary']['total']}")
    if args.strict and decision != "WATCH_CONTINUE":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
