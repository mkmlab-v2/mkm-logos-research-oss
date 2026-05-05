from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _top_insights(insight_7: Dict[str, Any], top_n: int = 3) -> list[Dict[str, Any]]:
    scored: list[tuple[str, float]] = []
    for key, raw_value in insight_7.items():
        try:
            scored.append((key, float(raw_value)))
        except (TypeError, ValueError):
            continue
    scored.sort(key=lambda item: item[1], reverse=True)
    return [{"name": name, "score": round(score, 6)} for name, score in scored[:top_n]]


def _fallback(value: Any, default: Any = None) -> Any:
    return value if value is not None else default


def _build_shadow_pnl_summary(artifacts: Path) -> Dict[str, Any]:
    shadow = _read_json(artifacts / "shadow_pnl_guardrail_latest.json")
    if not shadow:
        return {
            "shadow_pnl_status": "NOT_AVAILABLE",
            "virtual_pnl_usd": None,
            "avoided_risk_usd": None,
            "commentary": "Shadow PnL artifact missing; continue with macro risk briefing only.",
        }

    impact = shadow.get("impact") or {}
    latest = impact.get("latest_cycle_impact") or {}
    decision_state = (shadow.get("state") or {}).get("decision_state")
    operator_action = (shadow.get("state") or {}).get("operator_action")

    virtual_pnl = _fallback(impact.get("delta_usd_vs_prev_cycle"), 0.0)
    avoided_risk = _fallback(latest.get("avoided_loss_usd"), 0.0)
    missed = _fallback(latest.get("missed_opportunity_usd"), 0.0)
    commentary = (
        f"decision_state={decision_state}, operator_action={operator_action}, "
        f"avoided_risk_usd={avoided_risk}, missed_opportunity_usd={missed}"
    )
    return {
        "shadow_pnl_status": "OK",
        "virtual_pnl_usd": virtual_pnl,
        "avoided_risk_usd": avoided_risk,
        "commentary": commentary,
    }


def _build_payload() -> Dict[str, Any]:
    root = _root()
    artifacts = root / "docs" / "final" / "artifacts"

    smoke = _read_json(artifacts / "macro_risk_warning_api_smoke_latest.json")
    dashboard = _read_json(artifacts / "mkm_trackc_ops_dashboard_latest.json")
    handoff = _read_json(artifacts / "mkm_trackc_client_handoff_package_latest.json")
    shadow_pnl = _build_shadow_pnl_summary(artifacts)

    trackc = dashboard.get("trackc", {})
    system = dashboard.get("system", {})
    exec_summary = handoff.get("executive_summary", {})
    delivery = handoff.get("delivery_checklist", {})

    top_risks = _top_insights(smoke.get("insight_7", {}), top_n=3)
    recommended_posture = _fallback(
        smoke.get("recommended_operator_posture"),
        trackc.get("api_decision_state"),
    )

    payload = {
        "schema": "trackc_macro_risk_morning_briefing_v1",
        "generated_at_utc": _utc_now(),
        "briefing_date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "status": {
            "system_status": system.get("status"),
            "packet_status": trackc.get("packet_status"),
            "guard_passed": trackc.get("guard_passed"),
            "showroom_go_no_go": trackc.get("showroom_go_no_go"),
        },
        "market_snapshot": {
            "asset_scope": smoke.get("asset_scope"),
            "decision_state": smoke.get("decision_state"),
            "risk_warning_level": smoke.get("risk_warning_level"),
            "confidence_band": smoke.get("confidence_band"),
            "primary_regime_id": (smoke.get("regime_context") or {}).get("primary_regime_id"),
            "recommended_operator_posture": recommended_posture,
            "ttl_seconds": smoke.get("ttl_seconds"),
        },
        "top_risk_signals": top_risks,
        "shadow_pnl": shadow_pnl,
        "action_frame": {
            "label": _fallback(smoke.get("decision_state"), "WATCH"),
            "operator_action": _fallback(recommended_posture, "watch_tighten"),
            "veto_or_guard": "guard_ok" if trackc.get("guard_passed") else "guard_check_required",
            "next_check_hint": "Respect ttl_seconds and scheduled refresh chain.",
        },
        "fact_lock_evidence": {
            "smoke_artifact": "docs/final/artifacts/macro_risk_warning_api_smoke_latest.json",
            "dashboard_artifact": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json",
            "handoff_artifact": "docs/final/artifacts/mkm_trackc_client_handoff_package_latest.json",
            "shadow_pnl_artifact": "docs/final/artifacts/shadow_pnl_guardrail_latest.json",
            "delivery_ready": {
                "commercial_package_ready": delivery.get("commercial_package_ready"),
                "external_onepager_ready": delivery.get("external_onepager_ready"),
                "api_spec_package_ready": delivery.get("api_spec_package_ready"),
            },
        },
        "disclaimer": {
            "advisory_only": True,
            "no_buy_sell_instruction": True,
            "operator_final_decision": True,
        },
        "context": {
            "elevator_pitch": exec_summary.get("elevator_pitch"),
            "api_decision_state_from_handoff": exec_summary.get("api_decision_state"),
            "showroom_go_no_go_from_handoff": exec_summary.get("showroom_go_no_go"),
        },
    }
    return payload


def _render_ko(payload: Dict[str, Any]) -> str:
    mkt = payload["market_snapshot"]
    status = payload["status"]
    action = payload["action_frame"]
    shadow = payload["shadow_pnl"]
    top = payload["top_risk_signals"]
    risk_lines = "\n".join(
        f"- {item['name']}: `{item['score']}`" for item in top
    ) or "- (insight_7 unavailable)"

    return (
        "# Track C Macro Risk Morning Briefing (KR)\n\n"
        f"- generated_at_utc: `{payload['generated_at_utc']}`\n"
        f"- briefing_date_utc: `{payload['briefing_date_utc']}`\n\n"
        "## Status\n"
        f"- system_status: `{status.get('system_status')}`\n"
        f"- packet_status: `{status.get('packet_status')}`\n"
        f"- guard_passed: `{status.get('guard_passed')}`\n"
        f"- showroom_go_no_go: `{status.get('showroom_go_no_go')}`\n\n"
        "## Market Snapshot\n"
        f"- asset_scope: `{mkt.get('asset_scope')}`\n"
        f"- decision_state: `{mkt.get('decision_state')}`\n"
        f"- risk_warning_level: `{mkt.get('risk_warning_level')}`\n"
        f"- confidence_band: `{mkt.get('confidence_band')}`\n"
        f"- primary_regime_id: `{mkt.get('primary_regime_id')}`\n"
        f"- recommended_operator_posture: `{mkt.get('recommended_operator_posture')}`\n"
        f"- ttl_seconds: `{mkt.get('ttl_seconds')}`\n\n"
        "## Top Risk Signals\n"
        f"{risk_lines}\n\n"
        "## Shadow PnL Summary\n"
        f"- shadow_pnl_status: `{shadow.get('shadow_pnl_status')}`\n"
        f"- virtual_pnl_usd: `{shadow.get('virtual_pnl_usd')}`\n"
        f"- avoided_risk_usd: `{shadow.get('avoided_risk_usd')}`\n"
        f"- commentary: {shadow.get('commentary')}\n\n"
        "## Action Frame\n"
        f"- label: `{action.get('label')}`\n"
        f"- operator_action: `{action.get('operator_action')}`\n"
        f"- veto_or_guard: `{action.get('veto_or_guard')}`\n"
        f"- next_check_hint: {action.get('next_check_hint')}\n\n"
        "## Fact-Lock Evidence\n"
        f"- `{payload['fact_lock_evidence']['smoke_artifact']}`\n"
        f"- `{payload['fact_lock_evidence']['dashboard_artifact']}`\n"
        f"- `{payload['fact_lock_evidence']['handoff_artifact']}`\n\n"
        f"- `{payload['fact_lock_evidence']['shadow_pnl_artifact']}`\n\n"
        "## Disclaimer\n"
        "- Advisory only. Not investment advice.\n"
        "- No buy/sell instruction.\n"
        "- Final decision is always with the operator.\n"
    )


def _render_en(payload: Dict[str, Any]) -> str:
    mkt = payload["market_snapshot"]
    status = payload["status"]
    action = payload["action_frame"]
    shadow = payload["shadow_pnl"]
    top = payload["top_risk_signals"]
    risk_lines = "\n".join(
        f"- {item['name']}: `{item['score']}`" for item in top
    ) or "- (insight_7 unavailable)"

    return (
        "# Track C Macro Risk Morning Briefing (EN)\n\n"
        f"- generated_at_utc: `{payload['generated_at_utc']}`\n"
        f"- briefing_date_utc: `{payload['briefing_date_utc']}`\n\n"
        "## Status\n"
        f"- system_status: `{status.get('system_status')}`\n"
        f"- packet_status: `{status.get('packet_status')}`\n"
        f"- guard_passed: `{status.get('guard_passed')}`\n"
        f"- showroom_go_no_go: `{status.get('showroom_go_no_go')}`\n\n"
        "## Market Snapshot\n"
        f"- asset_scope: `{mkt.get('asset_scope')}`\n"
        f"- decision_state: `{mkt.get('decision_state')}`\n"
        f"- risk_warning_level: `{mkt.get('risk_warning_level')}`\n"
        f"- confidence_band: `{mkt.get('confidence_band')}`\n"
        f"- primary_regime_id: `{mkt.get('primary_regime_id')}`\n"
        f"- recommended_operator_posture: `{mkt.get('recommended_operator_posture')}`\n"
        f"- ttl_seconds: `{mkt.get('ttl_seconds')}`\n\n"
        "## Top Risk Signals\n"
        f"{risk_lines}\n\n"
        "## Shadow PnL Summary\n"
        f"- shadow_pnl_status: `{shadow.get('shadow_pnl_status')}`\n"
        f"- virtual_pnl_usd: `{shadow.get('virtual_pnl_usd')}`\n"
        f"- avoided_risk_usd: `{shadow.get('avoided_risk_usd')}`\n"
        f"- commentary: {shadow.get('commentary')}\n\n"
        "## Action Frame\n"
        f"- label: `{action.get('label')}`\n"
        f"- operator_action: `{action.get('operator_action')}`\n"
        f"- veto_or_guard: `{action.get('veto_or_guard')}`\n"
        f"- next_check_hint: {action.get('next_check_hint')}\n\n"
        "## Fact-Lock Evidence\n"
        f"- `{payload['fact_lock_evidence']['smoke_artifact']}`\n"
        f"- `{payload['fact_lock_evidence']['dashboard_artifact']}`\n"
        f"- `{payload['fact_lock_evidence']['handoff_artifact']}`\n\n"
        f"- `{payload['fact_lock_evidence']['shadow_pnl_artifact']}`\n\n"
        "## Disclaimer\n"
        "- Advisory only. Not investment advice.\n"
        "- No buy/sell instruction.\n"
        "- Final decision remains with the human operator.\n"
    )


def main() -> int:
    root = _root()
    artifacts = root / "docs" / "final" / "artifacts"
    payload = _build_payload()

    out_json = artifacts / "trackc_macro_risk_morning_briefing_latest.json"
    out_ko = artifacts / "trackc_macro_risk_morning_briefing_latest.ko.md"
    out_en = artifacts / "trackc_macro_risk_morning_briefing_latest.en.md"

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_ko.write_text(_render_ko(payload), encoding="utf-8")
    out_en.write_text(_render_en(payload), encoding="utf-8")

    print(f"briefing json written: {out_json}")
    print(f"briefing ko markdown written: {out_ko}")
    print(f"briefing en markdown written: {out_en}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
