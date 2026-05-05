#!/usr/bin/env python3
"""Build MKM commander hyperpersonalized report v2.1 (Fact/Hypothesis split)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

PATH_A_TRACK = ART / "a_track_go_nogo_status_latest.json"
PATH_BACKTEST = ART / "prophecy_lens_combo_backtest_v1_latest.json"
PATH_COMMANDER = ROOT / "reports" / "commander_myeongni_lens_latest.json"
PATH_SASANG_VETO = ART / "sasang_veto_only_active_config_latest.json"
PATH_TEMPLATE = ART / "mkm_myeongni_hyperpersonalized_template_v2_1.json"
PATH_OUT = ROOT / "reports" / "commander_hyperpersonalized_report_v2_1_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    a_track = _read_json(PATH_A_TRACK)
    backtest = _read_json(PATH_BACKTEST)
    commander = _read_json(PATH_COMMANDER)
    sasang_veto = _read_json(PATH_SASANG_VETO)
    template = _read_json(PATH_TEMPLATE)

    result = a_track.get("result", {})
    snap = a_track.get("snapshot", {})
    best = backtest.get("best_strategy", {})
    metrics = best.get("metrics", {})
    scores = commander.get("scores", {})
    mso = commander.get("myeongri_stream_outputs", {})
    advanced = commander.get("advanced", {})
    input_summary = advanced.get("input_summary", {})
    pillars = input_summary.get("pillars", {})
    hard_guardrails = sasang_veto.get("hard_guardrails", {})

    report: dict[str, Any] = {
        "schema": "mkm_commander_hyperpersonalized_report_v2_1",
        "version": "2.1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "template_schema": template.get("schema"),
        "labels": {
            "fact": "[FACT]",
            "hypothesis": "[HYPOTHESIS]",
            "governance_policy": "[GOVERNANCE_POLICY]",
            "non_medical": "[NON_MEDICAL]",
        },
        "meta": {
            "subject": "commander_personalization",
            "mode": "fact_lock_split",
            "source_paths": {
                "a_track": str(PATH_A_TRACK),
                "backtest": str(PATH_BACKTEST),
                "commander_lens": str(PATH_COMMANDER),
                "sasang_veto": str(PATH_SASANG_VETO),
            },
        },
        "fact_layer": {
            "a_track": {
                "overall_go_no_go": result.get("overall_go_no_go"),
                "recommended_stage": result.get("recommended_stage"),
                "failed_reasons": result.get("failed_reasons"),
                "price_output_locked": snap.get("price_output_locked"),
                "high_reliability_decision": snap.get("high_reliability_decision"),
            },
            "commander_lens": {
                "confidence": scores.get("confidence"),
                "direction_score": scores.get("direction_score"),
                "state_id": mso.get("state_id"),
                "run_id": mso.get("run_id"),
                "pillars": pillars,
            },
            "backtest_best_strategy": {
                "strategy_id": best.get("strategy_id"),
                "n_days": metrics.get("n_days"),
                "mdd": metrics.get("mdd"),
                "sharpe": metrics.get("sharpe"),
            },
            "governance": {
                "most_conservative_wins": hard_guardrails.get("most_conservative_wins"),
                "directional_entry_disabled": hard_guardrails.get("directional_entry_disabled"),
            },
        },
        "hypothesis_layer": {
            "disclaimer": "Hypothesis layer is non-trigger and non-medical.",
            "narrative": {
                "jijangan_hypothesis": "Water/earth-heavy structure favors risk-filtered execution over impulsive expansion.",
                "lifestyle_hypothesis": "Decision quality improves when high-conviction actions are gated by recovery and pacing checks.",
                "stress_guard_hypothesis": "When fatigue rises, reduce size cap and defer irreversible decisions.",
            },
        },
        "execution_policy": {
            "size_only_overlay": True,
            "direction_override_allowed": False,
            "decision_contract": "GO/HOLD/WATCH must follow governance artifacts, not narrative hypothesis.",
        },
        "final_action": {
            "decision": result.get("overall_go_no_go"),
            "stage": result.get("recommended_stage"),
            "reason": "Fact-layer governance result takes precedence over hypothesis layer.",
        },
    }

    PATH_OUT.parent.mkdir(parents=True, exist_ok=True)
    PATH_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {PATH_OUT}")


if __name__ == "__main__":
    main()
