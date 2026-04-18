#!/usr/bin/env python3
"""Build daily brain-sync markdown from watchdog and KPI state."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent.parent
MEMORY_DIR = PROJECT_ROOT / "memory"
KPI_DIR = MEMORY_DIR / "kpi"
BRAIN_DIR = MEMORY_DIR / "brain_sync"
WATCHDOG_LOG = MEMORY_DIR / "watchdog_direct.log"
LATEST_KPI = KPI_DIR / "latest_kpi.json"
STATUS_JSON = MEMORY_DIR / "trading_daemon_status.json"
SLACK_ADVISORY_HISTORY = (
    WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "slack_advisory_history_latest.json"
)


def _safe_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _safe_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _git_status_short() -> list[str]:
    cmd = ["git", "status", "--short", "--", "projects/bitcoin-trading"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    if proc.returncode != 0:
        return ["git status failed"]
    lines = [x.rstrip() for x in proc.stdout.splitlines() if x.strip()]
    return lines[:25]


def _last_watchdog_lines(n: int = 25) -> list[str]:
    text = _safe_text(WATCHDOG_LOG)
    lines = [x for x in text.splitlines() if x.strip()]
    return lines[-n:]


def _exchange_snapshot_24h(status: dict) -> dict:
    raw = status.get("exchange_snapshot_24h")
    if isinstance(raw, dict):
        return raw
    return {
        "available": False,
        "fills_count": None,
        "realized_pnl": None,
        "commission": None,
        "funding_fee": None,
        "net": None,
    }


def _kpi_exchange_history_insight(limit: int = 288) -> dict:
    """
    Build lightweight insight from KPI JSONL history.
    limit=288 ~= 24h at 5min cadence (safe upper bound for mixed cadence).
    """
    history_files = sorted(KPI_DIR.glob("kpi_snapshot_*.jsonl"), reverse=True)
    if not history_files:
        return {"available": False, "reason": "no_kpi_history"}

    rows: list[dict] = []
    try:
        for line in history_files[0].read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    except Exception:
        return {"available": False, "reason": "kpi_read_error"}

    if not rows:
        return {"available": False, "reason": "empty_kpi_history"}

    tail = rows[-limit:]
    net_series: list[float] = []
    fills_series: list[float] = []
    for row in tail:
        net = row.get("exchange_snapshot_24h_net")
        fills = row.get("exchange_snapshot_24h_fills_count")
        if isinstance(net, (int, float)):
            net_series.append(float(net))
        if isinstance(fills, (int, float)):
            fills_series.append(float(fills))

    if not net_series:
        return {"available": False, "reason": "no_exchange_24h_series"}

    latest_net = net_series[-1]
    first_net = net_series[0]
    net_delta = latest_net - first_net
    max_net = max(net_series)
    min_net = min(net_series)

    latest_fills = fills_series[-1] if fills_series else None
    avg_net_per_fill = None
    if isinstance(latest_fills, (int, float)) and latest_fills > 0:
        avg_net_per_fill = latest_net / latest_fills

    return {
        "available": True,
        "samples": len(tail),
        "series_points": len(net_series),
        "net_first": round(first_net, 8),
        "net_latest": round(latest_net, 8),
        "net_delta": round(net_delta, 8),
        "net_min": round(min_net, 8),
        "net_max": round(max_net, 8),
        "fills_latest": int(latest_fills) if isinstance(latest_fills, (int, float)) else None,
        "avg_net_per_fill_latest": round(avg_net_per_fill, 8) if avg_net_per_fill is not None else None,
    }


def _kpi_dual_regime_state_insight(limit: int = 288) -> dict:
    """Aggregate state_id source and clamp signals from KPI JSONL history."""

    history_files = sorted(KPI_DIR.glob("kpi_snapshot_*.jsonl"), reverse=True)
    if not history_files:
        return {"available": False, "reason": "no_kpi_history"}

    rows: list[dict] = []
    try:
        for line in history_files[0].read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    except Exception:
        return {"available": False, "reason": "kpi_read_error"}

    if not rows:
        return {"available": False, "reason": "empty_kpi_history"}

    tail = rows[-limit:]
    source_counts: dict[str, int] = {}
    clamp_count = 0
    present_count = 0

    for row in tail:
        kpi = row.get("dual_regime_state_kpi")
        if not isinstance(kpi, dict):
            continue
        source = str(kpi.get("state_id_source") or "none")
        source_counts[source] = source_counts.get(source, 0) + 1
        if bool(kpi.get("state_id_present", False)):
            present_count += 1
        if bool(kpi.get("signal_registry_clamped", False)):
            clamp_count += 1

    samples = sum(source_counts.values())
    if samples <= 0:
        return {"available": False, "reason": "no_state_kpi_samples"}

    sorted_sources = dict(sorted(source_counts.items(), key=lambda kv: kv[1], reverse=True))
    return {
        "available": True,
        "samples": samples,
        "state_id_present_count": present_count,
        "state_id_present_ratio": round(present_count / samples, 6),
        "clamp_count": clamp_count,
        "clamp_ratio": round(clamp_count / samples, 6),
        "source_counts": sorted_sources,
        "top_source": next(iter(sorted_sources.keys()), "none"),
    }


def _slack_advisory_summary() -> dict:
    doc = _safe_json(SLACK_ADVISORY_HISTORY)
    if not doc:
        return {"available": False, "reason": "missing_or_invalid_report"}
    dual_counts = doc.get("dual_regime_state_advisory_decision_counts")
    override_counts = doc.get("auto_hold_override_advisory_decision_counts")
    if not isinstance(dual_counts, dict):
        dual_counts = {}
    if not isinstance(override_counts, dict):
        override_counts = {}
    dual_top = next(iter(dual_counts.keys()), None) if dual_counts else None
    override_top = next(iter(override_counts.keys()), None) if override_counts else None
    return {
        "available": True,
        "window_days": doc.get("window_days"),
        "rows_in_window": doc.get("rows_in_window"),
        "dual_top_decision": dual_top,
        "override_top_decision": override_top,
        "dual_counts": dual_counts,
        "override_counts": override_counts,
    }


def _unknown_ratio(counts: dict, total_rows: int) -> float | None:
    if not isinstance(counts, dict):
        return None
    if total_rows <= 0:
        return None
    try:
        unknown = int(counts.get("unknown", 0) or 0)
        return round(unknown / total_rows, 6)
    except Exception:
        return None


def main() -> int:
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    date_tag = now.strftime("%Y-%m-%d")

    kpi = _safe_json(LATEST_KPI)
    status = _safe_json(STATUS_JSON)
    exchange_24h = _exchange_snapshot_24h(status)
    exchange_insight = _kpi_exchange_history_insight()
    state_insight = _kpi_dual_regime_state_insight()
    slack_summary = _slack_advisory_summary()
    git_lines = _git_status_short()
    log_lines = _last_watchdog_lines(25)

    md = []
    md.append(f"# Brain Sync Daily Note ({date_tag})")
    md.append("")
    md.append("## 1) Runtime Snapshot")
    md.append(f"- scheduler_ready: {kpi.get('scheduler_ready')}")
    md.append(f"- kill_switch_on: {kpi.get('kill_switch_on')}")
    md.append(f"- heartbeat_age_min: {kpi.get('heartbeat_age_min')}")
    md.append(f"- status_running: {status.get('running')}")
    md.append(f"- restart_count: {status.get('restart_count')}")
    md.append(f"- error_count: {status.get('error_count')}")
    md.append(f"- symbol: {status.get('symbol')}")
    md.append(f"- testnet: {status.get('testnet')}")
    md.append(f"- enable_trading: {status.get('enable_trading')}")
    md.append("")
    md.append("## 2) Exchange Snapshot (24h, realized)")
    md.append(f"- available: {exchange_24h.get('available')}")
    md.append(f"- fills_count: {exchange_24h.get('fills_count')}")
    md.append(f"- realized_pnl: {exchange_24h.get('realized_pnl')}")
    md.append(f"- commission: {exchange_24h.get('commission')}")
    md.append(f"- funding_fee: {exchange_24h.get('funding_fee')}")
    md.append(f"- net: {exchange_24h.get('net')}")
    md.append("")
    md.append("## 3) Exchange Insight (history from KPI JSONL)")
    md.append(f"- available: {exchange_insight.get('available')}")
    if exchange_insight.get("available"):
        md.append(f"- samples: {exchange_insight.get('samples')} (series_points={exchange_insight.get('series_points')})")
        md.append(f"- net_first -> net_latest: {exchange_insight.get('net_first')} -> {exchange_insight.get('net_latest')} (delta={exchange_insight.get('net_delta')})")
        md.append(f"- net_range: min={exchange_insight.get('net_min')} / max={exchange_insight.get('net_max')}")
        md.append(f"- fills_latest: {exchange_insight.get('fills_latest')}")
        md.append(f"- avg_net_per_fill_latest: {exchange_insight.get('avg_net_per_fill_latest')}")
    else:
        md.append(f"- reason: {exchange_insight.get('reason')}")
    md.append("")
    md.append("## 4) Dual Regime State Insight")
    md.append(f"- available: {state_insight.get('available')}")
    if state_insight.get("available"):
        md.append(f"- samples: {state_insight.get('samples')}")
        md.append(
            f"- state_id_present: {state_insight.get('state_id_present_count')} "
            f"(ratio={state_insight.get('state_id_present_ratio')})"
        )
        md.append(f"- clamp_count: {state_insight.get('clamp_count')} (ratio={state_insight.get('clamp_ratio')})")
        md.append(f"- top_source: {state_insight.get('top_source')}")
        md.append(f"- source_counts: {state_insight.get('source_counts')}")
    else:
        md.append(f"- reason: {state_insight.get('reason')}")
    md.append("")
    md.append("## 5) Slack Advisory Summary")
    md.append(f"- available: {slack_summary.get('available')}")
    if slack_summary.get("available"):
        md.append(
            f"- window_days/rows: {slack_summary.get('window_days')} / {slack_summary.get('rows_in_window')}"
        )
        md.append(f"- dual_top_decision: {slack_summary.get('dual_top_decision')}")
        md.append(f"- override_top_decision: {slack_summary.get('override_top_decision')}")
        rows_in_window = int(slack_summary.get("rows_in_window") or 0)
        dual_unknown_ratio = _unknown_ratio(slack_summary.get("dual_counts") or {}, rows_in_window)
        override_unknown_ratio = _unknown_ratio(slack_summary.get("override_counts") or {}, rows_in_window)
        md.append(f"- dual_unknown_ratio: {dual_unknown_ratio}")
        md.append(f"- override_unknown_ratio: {override_unknown_ratio}")
        if (
            (dual_unknown_ratio is not None and dual_unknown_ratio >= 0.7)
            or (override_unknown_ratio is not None and override_unknown_ratio >= 0.7)
        ):
            md.append(
                "- advisory_data_quality_warning: unknown_ratio_high (review advisory instrumentation wiring)"
            )
    else:
        md.append(f"- reason: {slack_summary.get('reason')}")
    md.append("")
    md.append("## 6) Watchdog Event Summary")
    wd = kpi.get("watchdog", {}) if isinstance(kpi.get("watchdog"), dict) else {}
    md.append(f"- daemon_healthy_count: {wd.get('daemon_healthy')}")
    md.append(f"- daemon_started_count: {wd.get('daemon_started')}")
    md.append(f"- stale_restart_count: {wd.get('stale_restart')}")
    md.append(f"- kill_switch_event_count: {wd.get('kill_switch_events')}")
    md.append("")
    md.append("## 7) Git Drift (Top 25)")
    if git_lines:
        for line in git_lines:
            md.append(f"- `{line}`")
    else:
        md.append("- clean")
    md.append("")
    md.append("## 8) Last 25 Watchdog Logs")
    if log_lines:
        md.append("```text")
        md.extend(log_lines)
        md.append("```")
    else:
        md.append("- no watchdog logs")
    md.append("")
    md.append("## 9) Operator Decision")
    md.append("- Keep current mode / Pause with STOP.txt / Adjust threshold")

    content = "\n".join(md) + "\n"
    file_path = BRAIN_DIR / f"brain_sync_{now.strftime('%Y%m%d')}.md"
    latest = BRAIN_DIR / "latest.md"

    file_path.write_text(content, encoding="utf-8")
    latest.write_text(content, encoding="utf-8")

    print(str(file_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
