#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_float_or_none(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _pick(d: dict[str, Any], paths: list[tuple[str, ...]]) -> Any:
    for p in paths:
        cur: Any = d
        ok = True
        for k in p:
            if not isinstance(cur, dict) or k not in cur:
                ok = False
                break
            cur = cur[k]
        if ok:
            return cur
    return None


def _all_checks_true(v: Any) -> bool | None:
    if not isinstance(v, dict) or not v:
        return None
    vals = [x for x in v.values() if isinstance(x, bool)]
    if not vals:
        return None
    return all(vals)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare AGCT stage2 candidate metrics against locked baseline.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--baseline-json",
        type=Path,
        default=root / "reports" / "agct_sigma_locked_baseline_chain_v1_latest.json",
    )
    ap.add_argument(
        "--candidate-json",
        type=Path,
        default=root / "reports" / "agct_sasang_btrack_daily_chain_v1_latest.json",
    )
    ap.add_argument("--min-repro-trials", type=int, default=5)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_candidate_compare_v1_latest.json",
    )
    ns = ap.parse_args()

    baseline = _read_json(ns.baseline_json)
    candidate = _read_json(ns.candidate_json)

    baseline_status = str(_pick(baseline, [("summary", "status"), ("status",)]) or "unknown")
    baseline_repro_trials = int(
        _to_float_or_none(_pick(baseline, [("inputs", "repro_trials"), ("metrics", "latest_repro_trials")])) or 0
    )
    baseline_go = _to_float_or_none(_pick(baseline, [("summary", "repro_go_rate_mean"), ("metrics", "latest_go_rate")]))
    baseline_ti = _to_float_or_none(
        _pick(baseline, [("summary", "repro_transition_intensity_mean"), ("metrics", "latest_transition_intensity")])
    )

    candidate_status = str(_pick(candidate, [("summary", "status"), ("status",), ("decision",)]) or "unknown")
    candidate_decision = _pick(candidate, [("decision",), ("decision_label",), ("summary", "status")])
    candidate_decision = None if candidate_decision is None else str(candidate_decision)
    candidate_checks_all = _all_checks_true(_pick(candidate, [("checks",), ("summary", "checks")]))
    candidate_go = _to_float_or_none(_pick(candidate, [("summary", "repro_go_rate_mean"), ("metrics", "go_rate")]))
    candidate_ti = _to_float_or_none(
        _pick(candidate, [("summary", "repro_transition_intensity_mean"), ("metrics", "transition_intensity")])
    )

    delta_go = None if baseline_go is None or candidate_go is None else candidate_go - baseline_go
    delta_ti = None if baseline_ti is None or candidate_ti is None else candidate_ti - baseline_ti

    baseline_repro_hard_gate_ok = baseline_repro_trials >= int(ns.min_repro_trials)
    candidate_gate_ok = (candidate_decision == "GO_BTRACK") and (candidate_checks_all is not False)

    reasons: list[str] = []
    next_actions: list[str] = []
    if baseline_status not in {"PASS", "WARN"}:
        reasons.append("baseline_status_not_ok")
    if not baseline_repro_hard_gate_ok:
        reasons.append("baseline_repro_trials_below_hard_gate")
    if not candidate_gate_ok:
        reasons.append("candidate_gate_not_ok")
    if candidate_checks_all is False:
        reasons.append("candidate_checks_not_all_true")

    if baseline_status not in {"PASS", "WARN"}:
        label = "HOLD_STAGE2"
        next_actions.extend(
            [
                "Recover baseline pipeline status to PASS/WARN before stage2 promotion review.",
                "Re-run locked baseline chain with reproducibility gate satisfied.",
            ]
        )
    elif not baseline_repro_hard_gate_ok:
        label = "WATCH_STAGE2"
        next_actions.extend(
            [
                "Increase reproducibility trials to hard-gate threshold.",
                "Keep stage2 candidate in B-track observe-only mode.",
            ]
        )
    elif candidate_gate_ok:
        label = "GO_STAGE2_CANDIDATE"
        next_actions.extend(
            [
                "Proceed with stage2 observe-only rollout and monitor daily drift.",
                "Require at least one weekly strict checkpoint before controlled promotion.",
            ]
        )
    else:
        label = "WATCH_STAGE2"
        next_actions.extend(
            [
                "Tune candidate checks until GO_BTRACK and checks_all_true are restored.",
                "Do not bridge candidate into live lane automatically.",
            ]
        )

    payload = {
        "schema": "agct_sasang_stage2_candidate_compare_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "baseline_json": str(ns.baseline_json.resolve()),
            "candidate_json": str(ns.candidate_json.resolve()),
            "min_repro_trials": int(ns.min_repro_trials),
        },
        "baseline": {
            "status": baseline_status,
            "repro_trials": baseline_repro_trials,
            "go_rate": baseline_go,
            "transition_intensity": baseline_ti,
        },
        "candidate": {
            "status": candidate_status,
            "decision_label": candidate_decision,
            "checks_pass_all": candidate_checks_all,
            "go_rate": candidate_go,
            "transition_intensity": candidate_ti,
        },
        "comparison": {
            "baseline_repro_hard_gate_ok": baseline_repro_hard_gate_ok,
            "candidate_gate_ok": candidate_gate_ok,
            "delta_go_rate": delta_go,
            "delta_transition_intensity": delta_ti,
        },
        "decision": {
            "label": label,
            "reasons": reasons,
            "next_actions": next_actions,
        },
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} label={label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
