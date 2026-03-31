# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.4, M:0.7}
# Balance: 90
# Purpose: Build compact broadcast summary from Fact-Safe brief.
# Keywords: broadcast, brief, gate, summary
"""Create a compact broadcast note from fact-safe multilens outputs."""

from __future__ import annotations

import json
import re
import argparse
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FACT_SAFE_BRIEF = ROOT / "docs" / "final" / "artifacts" / "fact_safe_multilens_brief_latest.md"
WAITING_LOG = ROOT / "docs" / "final" / "artifacts" / "waiting_queue_monthly_check_log.jsonl"
OUT_DIR = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "briefs"
OUT_MD = OUT_DIR / "fact_safe_multilens_broadcast_latest.md"
OUT_JSON = OUT_DIR / "fact_safe_multilens_broadcast_latest.json"
MONTHLY_PROPHECY_JSON = ROOT / "docs" / "final" / "artifacts" / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
REQUIRED_BRIEF_KEYS = [
    "reliability_badge",
    "high_reliability_decision",
    "gate_reason",
    "net",
]


def _extract(md: str, key: str) -> str | None:
    match = re.search(rf"- {re.escape(key)}:\s*(.+)", md)
    if not match:
        return None
    return match.group(1).strip()


def _latest_waiting_log() -> dict:
    if not WAITING_LOG.exists():
        return {}
    lines = [x for x in WAITING_LOG.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]
    if not lines:
        return {}
    try:
        row = json.loads(lines[-1])
        return row if isinstance(row, dict) else {}
    except Exception:
        return {}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Fact-Safe broadcast payload from latest brief artifacts.")
    parser.add_argument(
        "--strict-required",
        action="store_true",
        help="Fail when required brief keys are missing.",
    )
    return parser.parse_args()


def _monthly_outlook_for_now() -> dict:
    if not MONTHLY_PROPHECY_JSON.exists():
        return {}
    try:
        doc = json.loads(MONTHLY_PROPHECY_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}
    rows = doc.get("months")
    if not isinstance(rows, list):
        return {}
    month_now = datetime.now(timezone.utc).month
    hit = next((r for r in rows if isinstance(r, dict) and r.get("month") == month_now), None)
    if not isinstance(hit, dict):
        return {}
    kospi = hit.get("kospi") if isinstance(hit.get("kospi"), dict) else {}
    btc = hit.get("btc") if isinstance(hit.get("btc"), dict) else {}
    return {
        "month": month_now,
        "phase": hit.get("phase"),
        "kospi_direction": kospi.get("direction"),
        "btc_direction": btc.get("direction"),
        "kospi_down_pct": kospi.get("down_pct"),
        "btc_down_pct": btc.get("down_pct"),
    }


def _next_month_risk_hint() -> str | None:
    if not MONTHLY_PROPHECY_JSON.exists():
        return None
    try:
        doc = json.loads(MONTHLY_PROPHECY_JSON.read_text(encoding="utf-8"))
    except Exception:
        return None
    rows = doc.get("months")
    if not isinstance(rows, list) or not rows:
        return None
    month_now = datetime.now(timezone.utc).month
    next_month = month_now + 1 if month_now < 12 else 1
    hit = next((r for r in rows if isinstance(r, dict) and r.get("month") == next_month), None)
    if not isinstance(hit, dict):
        return None
    phase = hit.get("phase")
    kospi = hit.get("kospi") if isinstance(hit.get("kospi"), dict) else {}
    btc = hit.get("btc") if isinstance(hit.get("btc"), dict) else {}
    kd = kospi.get("down_pct")
    bd = btc.get("down_pct")
    direction = f"KOSPI={kospi.get('direction')}, BTC={btc.get('direction')}"
    if isinstance(kd, int) and isinstance(bd, int):
        return f"{next_month}월 선행 리스크: {phase} 구간, 하방확률(KOSPI/BTC)={kd}/{bd}, 방향={direction}"
    return f"{next_month}월 선행 리스크: {phase} 구간, 방향={direction}"


def main() -> int:
    args = _parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    brief = FACT_SAFE_BRIEF.read_text(encoding="utf-8", errors="ignore") if FACT_SAFE_BRIEF.exists() else ""
    waiting = _latest_waiting_log()

    payload = {
        "ts_utc": now_utc,
        "source_brief_path": str(FACT_SAFE_BRIEF),
        "reliability_badge": _extract(brief, "reliability_badge"),
        "high_reliability_decision": _extract(brief, "high_reliability_decision"),
        "gate_reason": _extract(brief, "gate_reason"),
        "net": _extract(brief, "net"),
        "history_samples": _extract(brief, "history samples"),
        "history_net_delta": _extract(brief, "history net_delta"),
        "overlap_drift_alert": waiting.get("overlap_drift_alert"),
        "overlap_drift_alert_threshold": waiting.get("overlap_drift_alert_threshold"),
    }
    payload["monthly_outlook"] = _monthly_outlook_for_now()
    payload["next_month_risk_hint"] = _next_month_risk_hint()
    missing_required = [k for k in REQUIRED_BRIEF_KEYS if not payload.get(k)]
    payload["required_keys_complete"] = len(missing_required) == 0
    payload["missing_required_keys"] = missing_required

    lines = [
        "# Fact-Safe Broadcast (Latest)",
        "",
        f"- generated_at_utc: {payload['ts_utc']}",
        f"- reliability_badge: {payload['reliability_badge']}",
        f"- high_reliability_decision: {payload['high_reliability_decision']}",
        f"- gate_reason: {payload['gate_reason']}",
        f"- net: {payload['net']}",
        f"- history_samples: {payload['history_samples']}",
        f"- history_net_delta: {payload['history_net_delta']}",
        f"- overlap_drift_alert: {payload['overlap_drift_alert']} (threshold={payload['overlap_drift_alert_threshold']})",
        (
            f"- monthly_outlook: {payload['monthly_outlook'].get('month')}월 "
            f"(phase={payload['monthly_outlook'].get('phase')}, "
            f"KOSPI={payload['monthly_outlook'].get('kospi_direction')}, "
            f"BTC={payload['monthly_outlook'].get('btc_direction')})"
            if payload["monthly_outlook"]
            else "- monthly_outlook: unavailable"
        ),
        f"- next_month_risk_hint: {payload.get('next_month_risk_hint') or 'unavailable'}",
        "",
        "## 3-line summary",
        f"1) Reliability badge is {payload['reliability_badge']} with gate {payload['high_reliability_decision']}.",
        f"2) Gate reason is {payload['gate_reason']}; monthly overlap alert is {payload['overlap_drift_alert']}.",
        f"3) Post-execution net={payload['net']} and history_delta={payload['history_net_delta']} (samples={payload['history_samples']}).",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.strict_required and missing_required:
        print(f"Missing required keys: {', '.join(missing_required)}")
        return 1
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
