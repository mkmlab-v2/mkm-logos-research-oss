from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _confidence_score(trackc: Dict[str, Any], logos: Dict[str, Any], dual_leg: Dict[str, Any], fallback: Dict[str, Any]) -> int:
    score = 50.0

    # Track C governance baseline
    if (trackc.get("guard_passed") is True):
        score += 6.0
    if str(trackc.get("api_decision_state") or "").upper() == "WATCH":
        score += 2.0

    # Logos query reliability
    queries_error = _safe_float(logos.get("queries_error"), 1.0)
    if queries_error <= 0:
        score += 8.0
    else:
        score -= 8.0

    # Weekly gate
    weekly_gate = str(logos.get("weekly_gate_decision") or "").upper()
    if weekly_gate == "GO":
        score += 6.0
    else:
        score -= 6.0

    # KOSPI leg evidence penalty
    kospi_n = _safe_float(((dual_leg.get("legs") or {}).get("kospi") or {}).get("n_evaluated"), 0.0)
    if kospi_n <= 0:
        score -= 10.0
    else:
        score += 6.0

    # Fallback signal
    signal = str((fallback.get("summary") or {}).get("signal") or "").upper()
    if signal == "GO":
        score += 4.0
    elif signal == "WATCH":
        score -= 6.0
    else:
        score -= 10.0

    return max(0, min(100, int(round(score))))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    art = root / "docs" / "final" / "artifacts"

    krx_open = True
    market_session_ko = "개장일(근무일)"
    try:
        from scripts.commander_market_session_calendar_v1 import krx_session_status  # noqa: WPS433

        krx = krx_session_status()
        krx_open = bool(krx.get("trading_today"))
        market_session_ko = str(krx.get("label_ko") or market_session_ko)
    except Exception:
        pass

    dashboard = _read_json(art / "mkm_trackc_ops_dashboard_latest.json")
    logos_insight = _read_json(art / "logos_shadow_insight_latest.json")
    dual_leg = _read_json(art / "trackc_prophecy_dual_leg_brief_latest.json")
    fallback = _read_json(art / "fallback_post_cutoff_watch_report_latest.json")

    trackc = dashboard.get("trackc") or {}
    logos_summary = logos_insight.get("summary") or {}
    confidence = _confidence_score(trackc, logos_summary, dual_leg, fallback)

    final_action = "WATCH"
    if confidence < 45:
        final_action = "HOLD"
    elif confidence >= 75:
        final_action = "GO_CONDITIONAL"
    if not krx_open:
        final_action = "HOLD"
        confidence = min(confidence, 40)

    report = {
        "schema": "internal_kospi_morning_brief_onepager_v1",
        "generated_at_utc": _utc_now(),
        "today_action": final_action,
        "confidence_0_100": confidence,
        "krx_trading_today": krx_open,
        "market_session_ko": market_session_ko,
        "system_status": (dashboard.get("system") or {}).get("status"),
        "promotion_decision": (dashboard.get("system") or {}).get("promotion_decision"),
        "trackc_api_decision_state": trackc.get("api_decision_state"),
        "logos_weekly_gate_decision": logos_summary.get("weekly_gate_decision"),
        "logos_queries_ok": logos_summary.get("queries_ok"),
        "logos_queries_error": logos_summary.get("queries_error"),
        "dual_leg_kospi_n_evaluated": ((dual_leg.get("legs") or {}).get("kospi") or {}).get("n_evaluated"),
        "dual_leg_kospi_hit_rate": ((dual_leg.get("legs") or {}).get("kospi") or {}).get("price_directional_hit_rate"),
        "fallback_signal": (fallback.get("summary") or {}).get("signal"),
        "evidence_paths": [
            "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json",
            "docs/final/artifacts/logos_shadow_insight_latest.json",
            "docs/final/artifacts/trackc_prophecy_dual_leg_brief_latest.json",
            "docs/final/artifacts/fallback_post_cutoff_watch_report_latest.json",
        ],
    }

    out_md = art / "internal_kospi_morning_brief_onepager_latest.md"
    out_json = art / "internal_kospi_morning_brief_onepager_latest.json"

    md = [
        "# Internal KOSPI Morning Brief (One Pager)",
        "",
        f"- schema: `{report['schema']}`",
        f"- generated_at_utc: `{report['generated_at_utc']}`",
        "- audience: `internal_only`",
        "",
        "## A) Final Call (Quick)",
        "",
        f"- today_action: `{report['today_action']}`",
        f"- market_session: `{report.get('market_session_ko', '—')}` (krx_trading_today={report.get('krx_trading_today')})",
        f"- conviction: `{report['confidence_0_100']} / 100`",
        "- execution_mode: `non-gating advisory`",
        "",
        "## B) Why (30-second read)",
        "",
        f"- system_status: `{report['system_status']}` / promotion_decision: `{report['promotion_decision']}`",
        f"- trackc_api_decision_state: `{report['trackc_api_decision_state']}`",
        f"- logos_weekly_gate_decision: `{report['logos_weekly_gate_decision']}`",
        f"- logos_queries_ok/error: `{report['logos_queries_ok']} / {report['logos_queries_error']}`",
        f"- kospi_n_evaluated: `{report['dual_leg_kospi_n_evaluated']}`",
        f"- kospi_hit_rate: `{report['dual_leg_kospi_hit_rate']}`",
        f"- fallback_signal: `{report['fallback_signal']}`",
        "",
        "## C) Operator Checklist",
        "",
        "- [ ] confirm artifact freshness",
        "- [ ] confirm no new guardrail failure",
        f"- [ ] keep action `{report['today_action']}` unless new KOSPI evidence appears",
        "",
        "## D) Evidence Paths",
        "",
        *[f"- `{p}`" for p in report["evidence_paths"]],
        "",
        "Confidence: computed from governance/query reliability + KOSPI evidence coverage.",
        f"Evidence: {', '.join(report['evidence_paths'])}",
        "Uncertainty trigger: if fallback signal degrades or KOSPI leg remains unpopulated.",
    ]

    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"onepager md written: {out_md}")
    print(f"onepager json written: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
