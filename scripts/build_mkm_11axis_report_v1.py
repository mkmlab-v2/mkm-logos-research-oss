#!/usr/bin/env python3
"""Build MKM 11-axis markdown report with evidence tiers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_MD = ART / "mkm_11axis_report_latest.md"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    gate = _safe_json(ART / "sasang_4agent_promotion_gate_latest.json")
    monitor = _safe_json(ART / "sasang_4agent_monitor_snapshot_latest.json")
    protocol = _safe_json(ART / "sasang_4agent_collision_btrack_protocol_latest.json")
    go_no_go = _safe_json(ART / "trading_go_no_go_latest.json")

    friction_fail = bool(monitor.get("alert"))
    survival_fail = str(go_no_go.get("go_no_go") or "NO_GO") != "GO"
    action = "HOLD" if (friction_fail or survival_fail) else "WATCH"

    metrics = (protocol.get("results") or {}) if isinstance(protocol.get("results"), dict) else {}
    mdd_reduction = float(metrics.get("mdd_reduction_abs") or 0.0)
    sig = bool(metrics.get("statistical_significance_pass_p_lt_0_05"))
    hold_ratio = float(metrics.get("hold_ratio") or 0.0)
    topo_p95 = float(metrics.get("topological_variance_p95") or 0.0)

    lines = [
        "# MKM 11-Axis Report",
        "",
        "## Header",
        "- report_id: `mkm_11axis_report_v1`",
        f"- generated_at_utc: `{_now_utc()}`",
        "- scope: `sasang_4agent / current runtime snapshot`",
        "- policy: `Most Conservative Wins`",
        "",
        "## Axis 1 — Pathology",
        "- verdict: [HYPO] High-volatility pathology interpretation remains heuristic.",
        "",
        "## Axis 2 — Temperament",
        "- verdict: [HYPO] Behavioral drift risk exists during fast trend reversals.",
        "",
        "## Axis 3 — Coupling",
        "- verdict: [ESTIMATE] Coupling map is model-derived and non-contractual.",
        "",
        "## Axis 4 — Transition Dynamics",
        "- verdict: [ESTIMATE] Transition dynamics require additional walk-forward calibration.",
        "",
        "## Axis 5 — Mass Sentiment",
        "- verdict: [ESTIMATE] Sentiment proxy is partial and should be treated as supporting evidence.",
        "",
        "## Axis 6 — Metal-Fire Equilibrium",
        "- verdict: [ESTIMATE] Equilibrium score is interpretable but not direct execution trigger.",
        "",
        "## Axis 7 — Survival Axis (Bomyeong)",
        (
            f"- verdict: [FACT] {'FAIL' if survival_fail else 'PASS'} "
            f"(trading_go_no_go={go_no_go.get('go_no_go', 'UNKNOWN')})"
        ),
        "",
        "## Axis 8 — Strategic Pharma Vector",
        "- verdict: [ESTIMATE] Position sizing guidance is conditional and non-binding.",
        "",
        "## Axis 9 — Execution Friction",
        (
            f"- verdict: [FACT] {'FAIL' if friction_fail else 'PASS'} "
            f"(monitor_alert={monitor.get('alert', 'UNKNOWN')}, hold_ratio={hold_ratio:.6f}, topo_p95={topo_p95:.6f})"
        ),
        "",
        "## Axis 10 — Math Alignment",
        f"- verdict: [FACT] {'PASS' if sig else 'FAIL'} (mdd_reduction_abs={mdd_reduction:.12f}, significance_pass={sig})",
        "",
        "## Axis 11 — Calibration Loop",
        "- verdict: [ESTIMATE] Calibration remains in low-alpha guarded mode.",
        "",
        "## Hard Prohibitions",
        "- Never assert arbitrary slippage percentages without artifact evidence.",
        "- Never assert transition probabilities without reproducible computation output.",
        "- Never assert price levels without source-bound evidence.",
        "- If Axis 9 or Axis 7 fails as [FACT], final action MUST be HOLD.",
        "",
        "## Final Decision",
        f"- action: {action}",
        "- reason: Conservative policy gate derived from survival/friction facts.",
        "- evidence_summary:",
        "  - FACT count: 3",
        "  - ESTIMATE count: 6",
        "  - HYPO count: 2",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
