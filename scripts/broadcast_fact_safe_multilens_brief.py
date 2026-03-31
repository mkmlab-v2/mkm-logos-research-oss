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
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FACT_SAFE_BRIEF = ROOT / "docs" / "final" / "artifacts" / "fact_safe_multilens_brief_latest.md"
WAITING_LOG = ROOT / "docs" / "final" / "artifacts" / "waiting_queue_monthly_check_log.jsonl"
OUT_DIR = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "briefs"
OUT_MD = OUT_DIR / "fact_safe_multilens_broadcast_latest.md"
OUT_JSON = OUT_DIR / "fact_safe_multilens_broadcast_latest.json"


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


def main() -> int:
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
        "",
        "## 3-line summary",
        f"1) Reliability badge is {payload['reliability_badge']} with gate {payload['high_reliability_decision']}.",
        f"2) Gate reason is {payload['gate_reason']}; monthly overlap alert is {payload['overlap_drift_alert']}.",
        f"3) Post-execution net={payload['net']} and history_delta={payload['history_net_delta']} (samples={payload['history_samples']}).",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
