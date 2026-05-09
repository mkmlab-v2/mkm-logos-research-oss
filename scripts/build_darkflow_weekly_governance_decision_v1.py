#!/usr/bin/env python3
"""Build weekly governance decision for darkflow B-track chain."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_json(line: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(line)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def main() -> int:
    policy_path = ART / "darkflow_weekly_governance_policy_v1.json"
    trend_path = ART / "darkflow_ops_trend_summary_latest.json"
    dual_path = ART / "darkflow_btrack_dual_policy_report_latest.json"
    hist_path = REPORTS / "darkflow_ops_history_log.jsonl"

    for p in (policy_path, trend_path, dual_path, hist_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing required input: {p}")

    policy = _load(policy_path)
    trend = _load(trend_path)
    dual = _load(dual_path)

    window_runs = int(policy.get("window_runs", 7))
    rows: list[dict[str, Any]] = []
    for raw in hist_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        obj = _safe_json(raw)
        if obj:
            rows.append(obj)
    window = rows[-window_runs:] if len(rows) > window_runs else rows

    cons = [str(r.get("conservative_policy", "n/a")) for r in window]
    expl = [str(r.get("exploratory_policy", "n/a")) for r in window]
    cons_counter = Counter(cons)
    expl_counter = Counter(expl)

    c_continue = policy.get("continue_conditions", {})
    c_retune = policy.get("retune_conditions", {})
    c_stop = policy.get("stop_conditions", {})
    outcomes = policy.get("outcomes", {})

    exploratory_go_count = expl_counter.get("GO_RESEARCH", 0)
    conservative_hold_count = cons_counter.get("HOLD_INCONCLUSIVE", 0)
    exploratory_hold_count = expl_counter.get("HOLD_INCONCLUSIVE", 0)

    single_switch = int(trend.get("single_policy_switch_count", 0))
    top_switch = int(trend.get("top_hypothesis_switch_count", 0))
    freshness_pass_rate = float(trend.get("freshness_pass_rate", 0.0))

    stop_hit = (
        conservative_hold_count >= int(c_stop.get("min_conservative_hold_count", 6))
        or exploratory_hold_count >= int(c_stop.get("min_exploratory_hold_count", 4))
    )
    continue_hit = (
        exploratory_go_count >= int(c_continue.get("min_exploratory_go_count", 3))
        and single_switch <= int(c_continue.get("max_single_policy_switch_count", 2))
        and top_switch <= int(c_continue.get("max_top_hypothesis_switch_count", 1))
        and freshness_pass_rate >= float(c_continue.get("min_freshness_pass_rate", 0.8))
    )
    retune_hit = (
        single_switch >= int(c_retune.get("min_single_policy_switch_count", 3))
        or top_switch >= int(c_retune.get("min_top_hypothesis_switch_count", 2))
        or freshness_pass_rate <= float(c_retune.get("max_freshness_pass_rate", 0.79))
    )

    if stop_hit:
        decision = str(outcomes.get("stop", "PAUSE_AND_REFRAME"))
    elif continue_hit:
        decision = str(outcomes.get("continue", "CONTINUE_RESEARCH"))
    elif retune_hit:
        decision = str(outcomes.get("retune", "RETUNE_POLICY_OR_INPUTS"))
    else:
        decision = str(outcomes.get("retune", "RETUNE_POLICY_OR_INPUTS"))

    out = {
        "schema": "darkflow_weekly_governance_decision_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window_runs": window_runs,
        "decision": decision,
        "inputs": {
            "exploratory_go_count": exploratory_go_count,
            "conservative_hold_count": conservative_hold_count,
            "exploratory_hold_count": exploratory_hold_count,
            "single_policy_switch_count": single_switch,
            "top_hypothesis_switch_count": top_switch,
            "freshness_pass_rate": freshness_pass_rate,
            "latest_dual_decisions": {
                "conservative": (dual.get("conservative") or {}).get("decision", "n/a"),
                "exploratory": (dual.get("exploratory") or {}).get("decision", "n/a")
            }
        },
        "source_track": "B",
        "observation_mode": "RESEARCH_ONLY",
        "auto_bind_to_atrack_forbidden": True,
        "evidence_paths": {
            "policy": str(policy_path),
            "trend": str(trend_path),
            "dual": str(dual_path),
            "history_log": str(hist_path)
        }
    }

    out_json = ART / "darkflow_weekly_governance_decision_latest.json"
    out_md = ART / "darkflow_weekly_governance_decision_latest.md"
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Darkflow Weekly Governance Decision",
        "",
        f"- generated_at_utc: `{out['generated_at_utc']}`",
        f"- window_runs: `{window_runs}`",
        f"- decision: `{decision}`",
        "",
        "## Inputs",
        "",
        f"- exploratory_go_count: `{exploratory_go_count}`",
        f"- conservative_hold_count: `{conservative_hold_count}`",
        f"- exploratory_hold_count: `{exploratory_hold_count}`",
        f"- single_policy_switch_count: `{single_switch}`",
        f"- top_hypothesis_switch_count: `{top_switch}`",
        f"- freshness_pass_rate: `{freshness_pass_rate}`",
        ""
    ]
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
