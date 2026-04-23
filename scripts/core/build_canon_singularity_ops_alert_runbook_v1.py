#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, data: dict[str, Any]) -> None:
    o = data["ops_alert_summary"]
    r = data["recommended_action"]
    s = data["strict_auto_run"]
    f = data.get("freeze_v2_stability_gate") or {}
    st = data.get("observation_streak") or {}
    reasons = list(data.get("attention_reasons") or [])
    lines = [
        "# Canon Ops Alert Runbook v1",
        "",
        f"- generated_at_utc: {data['generated_at_utc']}",
        f"- ops_alert: {o['ops_alert']}",
        f"- severity: {o['severity']}",
        f"- consecutive_alert_count: {o['consecutive_alert_count']}",
        "",
        "## Recommended Action",
        f"- kind: {r['kind']}",
        f"- reason: {r['reason']}",
        f"- command: {r['command'] or 'none'}",
        "",
        "## Freeze V2 Stability",
        f"- status: {f.get('status', 'missing')}",
        f"- frozen_rate: {f.get('frozen_rate')}",
        f"- window_size: {f.get('window_size')}",
        "",
        "## Observation Streak",
        f"- verdict: {st.get('verdict', 'missing')}",
        f"- pass_count: {((st.get('metrics') or {}).get('pass_count'))}",
        f"- window_size_observed: {((st.get('metrics') or {}).get('window_size_observed'))}",
        f"- latest_verdict: {((st.get('metrics') or {}).get('latest_verdict'))}",
        "",
        "## Attention Reasons",
    ]
    if reasons:
        lines.extend([f"- {x}" for x in reasons])
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Strict Auto Run",
        f"- enabled: {s['enabled']}",
        f"- triggered: {s['triggered']}",
        f"- status: {s['status']}",
        f"- exit_code: {s['exit_code']}",
        f"- summary_path: {s['summary_path']}",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build one-page ops alert runbook from rehearsal latest artifact.")
    ap.add_argument(
        "--rehearsal-latest-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_rehearsal_status_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_ops_alert_runbook_latest.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_ops_alert_runbook_latest.md",
    )
    ap.add_argument(
        "--freeze-v2-stability-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json",
    )
    ap.add_argument(
        "--observation-streak-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_observation_streak_report_v1.json",
    )
    args = ap.parse_args()

    src = _read_json(Path(args.rehearsal_latest_json))
    freeze_from_latest = src.get("freeze_v2_stability_gate") or {}
    freeze_stability = _read_json(Path(args.freeze_v2_stability_gate_json))
    freeze_effective = freeze_from_latest if freeze_from_latest else {
        "status": str(freeze_stability.get("status") or "missing"),
        "window_size": int(((freeze_stability.get("metrics") or {}).get("window_size")) or 0),
        "frozen_rate": float(((freeze_stability.get("metrics") or {}).get("frozen_rate")) or 0.0),
        "generated_at_utc": str(freeze_stability.get("generated_at_utc") or ""),
    }
    streak = _read_json(Path(args.observation_streak_json))
    recommended_action = dict(src.get("recommended_action") or {})
    base_reason = str(recommended_action.get("reason") or "").strip()
    attention_reasons: list[str] = []
    if str(streak.get("verdict") or "") == "hold":
        attention_reasons.append("observation_streak_hold")
    if base_reason and base_reason.lower() not in {"none", "stable"}:
        attention_reasons.append(base_reason)
    if not base_reason:
        recommended_action["reason"] = attention_reasons[0] if attention_reasons else "none"

    out = {
        "schema": "original_corpus_regime_singularity_canon_ops_alert_runbook_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "rehearsal_latest_json": str(args.rehearsal_latest_json),
            "freeze_v2_stability_gate_json": str(args.freeze_v2_stability_gate_json),
            "observation_streak_json": str(args.observation_streak_json),
        },
        "task": src.get("task") or {},
        "drift_gate": src.get("drift_gate") or {},
        "ops_alert_summary": src.get("ops_alert_summary") or {},
        "recommended_action": recommended_action,
        "strict_auto_run": src.get("strict_auto_run") or {},
        "freeze_v2_stability_gate": freeze_effective,
        "observation_streak": {
            "verdict": str(streak.get("verdict") or "missing"),
            "metrics": dict(streak.get("metrics") or {}),
            "hold_reasons": list(streak.get("hold_reasons") or []),
            "generated_at_utc": str(streak.get("generated_at_utc") or ""),
        },
        "attention_reasons": attention_reasons,
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

