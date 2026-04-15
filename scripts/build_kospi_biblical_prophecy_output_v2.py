# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.9, K:0.5, M:0.7}
# Balance: 89
# Purpose: Build KOSPI biblical prophecy output v2 from latest artifacts.
# Keywords: biblical, KOSPI, prophecy, gate, automation
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ART = Path("docs/final/artifacts")
TEMPLATE_DEFAULT = ART / "kospi_biblical_prophecy_output_v2_template.json"
GATE_DEFAULT = ART / "kospi_biblical_single_lane_commercial_gate_autonomous_latest.json"
STATUS_DEFAULT = ART / "kospi_biblical_single_lane_stability_status_latest.json"
OUT_DEFAULT = ART / "kospi_biblical_prophecy_output_v2_latest.json"


def _load(path: Path) -> dict[str, Any]:
    # Some PowerShell-generated JSON files include UTF-8 BOM.
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _decide_action(gate: dict[str, Any], status: dict[str, Any]) -> tuple[str, str, str]:
    pre = bool(gate.get("precommercial_ready", False))
    stability_go = bool((gate.get("stability") or {}).get("stability_go", False))
    blockers = gate.get("blockers") or []
    ext_pass = bool(((gate.get("gates") or {}).get("external_reality_gate") or {}).get("external_reality_pass", False))
    dom_gate = bool(((gate.get("gates") or {}).get("external_reality_gate") or {}).get("dominant_share_gate", False))

    if stability_go:
        return (
            "candidate",
            "Stable streak satisfied; internal and external gates are aligned for commercialization candidate mode.",
            "none",
        )
    if pre and ext_pass and dom_gate:
        return (
            "hold",
            "Precommercial-ready but stability streak not yet complete; continue guarded run until stability_go.",
            "watch",
        )
    if blockers:
        return (
            "no-go",
            "Blocking gates remain active: " + ", ".join(str(x) for x in blockers),
            "alert",
        )
    return (
        "hold",
        "Waiting for additional evidence windows before escalation.",
        "watch",
    )


def build(template: dict[str, Any], gate: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    out = dict(template)
    out["generated_at_utc"] = _now_utc()
    out["timeframes"]["monthly"] = datetime.now(UTC).strftime("%Y-%m")
    out["timeframes"]["daily_eval_window"] = "30 recent sessions (with equivalent-n fallback)"

    internal = (gate.get("current_metrics") or {}).get("internal_equivalent_n") or (gate.get("current_metrics") or {}).get("internal") or {}
    external_active = (gate.get("current_metrics") or {}).get("external_active_for_gate") or (gate.get("current_metrics") or {}).get("external_recent_locked") or {}

    out["gates"]["internal_gate"]["pass"] = bool((gate.get("gates") or {}).get("internal_equivalent_n_gate", {}).get("accuracy_gate", False))
    out["gates"]["internal_gate"]["metrics"] = {
        "accuracy": float(internal.get("accuracy", 0.0)),
        "n_samples": int(internal.get("n_samples", 0)),
        "margin_vs_random": float(internal.get("margin_vs_random", 0.0)),
        "dominant_share": float(internal.get("dominant_share", 1.0)),
    }
    out["gates"]["internal_gate"]["evidence_path"] = str(
        (gate.get("inputs") or {}).get("promotion_json", "docs/final/artifacts/kospi_biblical_lane_promotion_report_v1_latest.json")
    )

    ext_gate = (gate.get("gates") or {}).get("external_reality_gate") or {}
    out["gates"]["external_reality_gate"]["pass"] = bool(ext_gate.get("external_reality_pass", False))
    out["gates"]["external_reality_gate"]["mode"] = str(ext_gate.get("mode", "recent"))
    out["gates"]["external_reality_gate"]["metrics"] = {
        "accuracy": float(external_active.get("accuracy", 0.0)),
        "n_samples": int(external_active.get("n_samples", 0)),
        "margin_vs_random": float(external_active.get("margin_vs_random", 0.0)),
        "dominant_share": float(external_active.get("dominant_share", 1.0)),
        "mixed_bull_capture": float(external_active.get("mixed_bull_capture", 0.0)),
    }
    out["gates"]["external_reality_gate"]["evidence_path"] = str(
        (gate.get("inputs") or {}).get("lock_json", "docs/final/artifacts/biblical_external_reality_gate_mixed_promoted_v1_latest.json")
    )

    st = gate.get("stability") or {}
    out["gates"]["stability_gate"]["precommercial_ready"] = bool(gate.get("precommercial_ready", False))
    out["gates"]["stability_gate"]["ready_streak"] = int(st.get("current_ready_streak", status.get("ready_streak", 0)))
    out["gates"]["stability_gate"]["streak_required"] = int(st.get("streak_required", status.get("streak_required", 3)))
    out["gates"]["stability_gate"]["streak_min_spacing_hours"] = float(
        st.get("streak_min_spacing_hours", status.get("streak_min_spacing_hours", 24.0))
    )
    out["gates"]["stability_gate"]["stability_go"] = bool(st.get("stability_go", status.get("stability_go", False)))

    mode = out["gates"]["external_reality_gate"]["mode"]
    if mode == "equivalent_n":
        regime = "mixed-equivalent"
    else:
        regime = "mixed-recent"

    ext_recent = (gate.get("current_metrics") or {}).get("external_recent_locked") or {}
    ext_active_metrics = out["gates"]["external_reality_gate"]["metrics"]
    recent_bull_capture = float(ext_recent.get("mixed_bull_capture", 0.0))
    active_dom = float(ext_active_metrics["dominant_share"])
    active_acc = float(ext_active_metrics["accuracy"])

    # 2026 tactical override:
    # If recent window shows clear bullish capture, use short-term bull baseline
    # while keeping medium-term invalidation conditions strict.
    tactical_bull = recent_bull_capture >= 0.30 and float(ext_recent.get("accuracy", 0.0)) >= 0.45
    direction = "bull" if tactical_bull else ("bear" if active_dom >= 0.5 else "bull")
    conf = max(0.0, min(1.0, active_acc))

    out["prophecy"]["base_scenario"]["regime_label"] = regime
    out["prophecy"]["base_scenario"]["direction_bias"] = direction
    out["prophecy"]["base_scenario"]["confidence"] = round(conf, 6)
    if tactical_bull:
        out["prophecy"]["base_scenario"]["thesis"] = (
            "Short-term risk-on is active; run bull baseline tactically while preserving strict drift/overheat guards."
        )
    else:
        out["prophecy"]["base_scenario"]["thesis"] = (
            "External reality gate stays aligned with equivalent-n fallback; maintain directional bias with strict drift watch."
        )
    out["prophecy"]["alternative_scenario"]["direction_bias"] = "bull" if direction == "bear" else "bear"
    out["prophecy"]["alternative_scenario"]["confidence"] = round(max(0.0, conf - 0.12), 6)
    out["prophecy"]["alternative_scenario"]["trigger_conditions"] = [
        "dominant_share rises above 0.70",
        "external_reality_pass turns false",
        "recent bull capture falls below 0.20"
    ]
    if tactical_bull:
        out["prophecy"]["alternative_scenario"]["thesis"] = (
            "If drift/overheat triggers fire, downgrade from short-term bull to defensive bear regime."
        )
    else:
        out["prophecy"]["alternative_scenario"]["thesis"] = "Flip bias only when external reality drift invalidates current regime fit."
    out["prophecy"]["invalidation_conditions"] = [
        "If external_reality_gate.pass = false, invalidate current month prophecy.",
        "If stability streak fails to progress on schedule, downgrade to research hold."
    ]

    action, reason, escalation = _decide_action(gate, status)
    out["operator_brief"]["today_action"] = action
    out["operator_brief"]["reason"] = reason
    out["operator_brief"]["escalation"] = escalation
    out["operator_brief"]["next_check_utc"] = str(
        status.get("next_eligible_streak_ts_utc", (datetime.now(UTC)).isoformat().replace("+00:00", "Z"))
    )

    lt = status.get("live_trading") if isinstance(status.get("live_trading"), dict) else None
    if lt is None:
        pre = bool(gate.get("precommercial_ready", False))
        sg = bool((gate.get("stability") or {}).get("stability_go", False))
        bl = gate.get("blockers") or []
        reasons: list[str] = []
        if not pre:
            reasons.append("precommercial_ready=false")
        if not sg:
            reasons.append("stability_go=false (streak not complete)")
        if bl:
            reasons.append("blockers: " + ", ".join(str(x) for x in bl))
        allowed = pre and sg and len(bl) == 0
        if allowed:
            phase = "live_eligible"
        elif sg:
            phase = "stable"
        elif pre:
            phase = "precommercial"
        else:
            phase = "research"
        lt = {
            "lane": "biblical_only",
            "policy": (
                "Biblical lane only; no myeongri/sasang fusion; order hook requires human limits + kill switch"
            ),
            "phase": phase,
            "allowed": allowed,
            "reasons_if_blocked": reasons,
            "note": "allowed=true means gate-evidence only; broker integration and sizing are out of band.",
        }
    out["live_trading"] = lt

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build KOSPI biblical prophecy output v2 latest")
    ap.add_argument("--template", type=Path, default=TEMPLATE_DEFAULT)
    ap.add_argument("--gate-json", type=Path, default=GATE_DEFAULT)
    ap.add_argument("--status-json", type=Path, default=STATUS_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    template = _load(args.template)
    gate = _load(args.gate_json)
    status = _load(args.status_json) if args.status_json.exists() else {}
    out = build(template, gate, status)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
