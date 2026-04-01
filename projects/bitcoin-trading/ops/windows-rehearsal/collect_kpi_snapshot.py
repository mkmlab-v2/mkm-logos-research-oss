#!/usr/bin/env python3
"""Collect direct-watchdog KPI snapshot for 7-day rehearsal."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
MEMORY_DIR = PROJECT_ROOT / "memory"
KPI_DIR = MEMORY_DIR / "kpi"
WATCHDOG_LOG = MEMORY_DIR / "watchdog_direct.log"
HEARTBEAT_FILE = MEMORY_DIR / "trading_daemon_heartbeat.txt"
STOP_FILE = MEMORY_DIR / "STOP.txt"
STATUS_FILE = MEMORY_DIR / "trading_daemon_status.json"
TRADER_STATE_FILE = PROJECT_ROOT / "logs" / "trading_state.json"
RISK_PROFILE_FILE = PROJECT_ROOT / "memory" / "v2" / "risk" / "risk_profile_fact_safe_latest.json"
LOGOS_TIMELINE_ANCHOR = (
    WORKSPACE_ROOT / "reports" / "constitution" / "btrack_pilot" / "logos_timeline_anchor_v1_latest.json"
)
LOGOS_TIMELINE_CALIBRATION = (
    WORKSPACE_ROOT
    / "reports"
    / "constitution"
    / "btrack_pilot"
    / "logos_timeline_tradition_calibration_latest.json"
)
TASK_NAMES = ("Bitcoin-KPI-Snapshot-30min", "Bitcoin-KPI-Snapshot-5min")


def _read_text(path: Path) -> str:
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


def _extract_singular_core_kpi(trader_state: dict) -> dict:
    counts = trader_state.get("singular_action_counts") or {}
    total = int(trader_state.get("signal_total_count", 0) or 0)
    buy = int(counts.get("BUY", 0) or 0)
    sell = int(counts.get("SELL", 0) or 0)
    locked = int(counts.get("LOCKED", 0) or 0)
    if total <= 0:
        return {
            "total_signals": 0,
            "buy_count": buy,
            "sell_count": sell,
            "locked_count": locked,
            "locked_ratio": None,
            "buy_ratio": None,
            "sell_ratio": None,
            "last_signal_summary": trader_state.get("last_signal_summary"),
        }
    return {
        "total_signals": total,
        "buy_count": buy,
        "sell_count": sell,
        "locked_count": locked,
        "locked_ratio": locked / total,
        "buy_ratio": buy / total,
        "sell_ratio": sell / total,
        "last_signal_summary": trader_state.get("last_signal_summary"),
    }


def _logos_timeline_status() -> dict:
    anchor = _safe_json(LOGOS_TIMELINE_ANCHOR)
    calib = _safe_json(LOGOS_TIMELINE_CALIBRATION)
    anchor_count = 0
    if isinstance(anchor.get("anchors"), list):
        anchor_count = len(anchor.get("anchors") or [])
    calib_samples = int(calib.get("sample_count_total", 0) or 0) if calib else 0
    calib_nonzero = int(calib.get("nonzero_pnl_samples", 0) or 0) if calib else 0
    calib_proxy = int(calib.get("proxy_pnl_samples", 0) or 0) if calib else 0
    calib_effective_nonzero = int(calib.get("effective_nonzero_samples", 0) or 0) if calib else 0
    calib_base = (
        ((calib.get("multipliers") or {}).get("base_by_tradition") or {})
        if isinstance(calib, dict)
        else {}
    )
    calib_samples_by_trad = (
        (calib.get("sample_count_by_tradition") or {})
        if isinstance(calib, dict)
        else {}
    )
    return {
        "anchor_exists": LOGOS_TIMELINE_ANCHOR.exists(),
        "anchor_schema": anchor.get("schema"),
        "anchor_count": anchor_count,
        "calibration_exists": LOGOS_TIMELINE_CALIBRATION.exists(),
        "calibration_schema": calib.get("schema"),
        "calibration_sample_count": calib_samples,
        "calibration_nonzero_pnl_samples": calib_nonzero,
        "calibration_proxy_pnl_samples": calib_proxy,
        "calibration_effective_nonzero_samples": calib_effective_nonzero,
        "calibration_sample_count_by_tradition": calib_samples_by_trad,
        "calibration_base_by_tradition": calib_base,
        "calibration_diagnostics": (calib.get("diagnostics") if isinstance(calib, dict) else {}),
    }


def _task_is_ready() -> bool:
    for task_name in TASK_NAMES:
        cmd = ["schtasks", "/Query", "/TN", task_name]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        stdout_text = proc.stdout or ""
        if proc.returncode == 0 and ("Ready" in stdout_text or "준비" in stdout_text):
            return True
    return False


def _heartbeat_age_minutes() -> float | None:
    raw = _read_text(HEARTBEAT_FILE).strip()
    if not raw:
        return None
    try:
        hb = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None
    if hb.tzinfo is None:
        # Daemon heartbeat currently writes local naive timestamps.
        now_local = datetime.now()
        return (now_local - hb).total_seconds() / 60.0
    now_utc = datetime.now(timezone.utc)
    return (now_utc - hb).total_seconds() / 60.0


def _watchdog_counters(log_text: str) -> dict:
    lines = log_text.splitlines()
    return {
        "log_lines": len(lines),
        "daemon_healthy": sum("Daemon healthy" in x for x in lines),
        "daemon_started": sum("Starting daemon process" in x for x in lines),
        "stale_restart": sum("heartbeat stale" in x.lower() for x in lines),
        "kill_switch_events": sum("STOP.txt exists" in x for x in lines),
    }


def _risk_profile_pipeline_status(status: dict) -> dict:
    # Prefer direct runtime profile metadata to avoid daemon-status cache lag.
    profile = _safe_json(RISK_PROFILE_FILE)
    if isinstance(profile, dict) and profile:
        source = str(profile.get("source") or "")
        mode = str(profile.get("mode") or "")
        freshness = {"has_generated_at": False, "is_fresh": None, "age_minutes": None, "max_age_minutes": 60}
        try:
            max_age = max(10, int(os.getenv("RISK_PROFILE_MAX_AGE_MINUTES", "60")))
        except Exception:
            max_age = 60
        generated_at = profile.get("generated_at")
        if generated_at:
            freshness["has_generated_at"] = True
            freshness["max_age_minutes"] = max_age
            try:
                dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
                now_ref = datetime.now(dt.tzinfo) if dt.tzinfo is not None else datetime.now()
                age = max(0.0, (now_ref - dt).total_seconds() / 60.0)
                freshness["age_minutes"] = round(age, 3)
                freshness["is_fresh"] = age <= float(max_age)
            except Exception:
                pass
        return {
            "status": "loaded",
            "source": source or None,
            "mode": mode or None,
            "is_n8n_source": ("n8n" in source.lower()) or ("n8n" in mode.lower()),
            "freshness": freshness,
        }

    risk_status = status.get("risk_profile") or {}
    return {
        "status": risk_status.get("status"),
        "source": risk_status.get("source"),
        "mode": risk_status.get("mode"),
        "is_n8n_source": risk_status.get("is_n8n_source"),
        "freshness": risk_status.get("freshness"),
    }


def _extract_dual_regime_state_kpi(status: dict, trader_state: dict) -> dict:
    """Extract latest state-source observability from signal summaries."""

    # Prefer runtime trader_state summary, then daemon status fallback.
    summary = {}
    if isinstance(trader_state, dict):
        summary = trader_state.get("last_signal_summary") or {}
    if not isinstance(summary, dict) or not summary:
        mkm_core = status.get("mkm_singular_core") if isinstance(status, dict) else {}
        if isinstance(mkm_core, dict):
            summary = mkm_core.get("last_signal_summary") or {}
    if not isinstance(summary, dict):
        summary = {}

    risk_assessment = summary.get("risk_assessment") or {}
    if not isinstance(risk_assessment, dict):
        risk_assessment = {}
    dual_ctx = risk_assessment.get("dual_regime_context") or {}
    if not isinstance(dual_ctx, dict):
        dual_ctx = {}

    state_id = dual_ctx.get("state_id")
    try:
        state_id_norm = int(state_id) if state_id is not None else None
    except Exception:
        state_id_norm = None
    if state_id_norm is not None and not (1 <= state_id_norm <= 16):
        state_id_norm = None

    state_source = str(dual_ctx.get("state_id_source") or "none")
    clamped = bool(risk_assessment.get("signal_registry_clamped", False))
    cap = risk_assessment.get("signal_registry_cap")
    try:
        cap_value = float(cap) if cap is not None else None
    except Exception:
        cap_value = None

    return {
        "state_id": state_id_norm,
        "state_id_source": state_source,
        "state_id_present": state_id_norm is not None,
        "signal_registry_clamped": clamped,
        "signal_registry_cap": cap_value,
        # Single-point counters for aggregation by downstream tools.
        "source_count": {state_source: 1},
        "clamp_count": 1 if clamped else 0,
        "sample_count": 1,
    }


def main() -> int:
    KPI_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    log_text = _read_text(WATCHDOG_LOG)
    status = _safe_json(STATUS_FILE)
    trader_state = _safe_json(TRADER_STATE_FILE)
    hb_age = _heartbeat_age_minutes()

    exchange_24h = status.get("exchange_snapshot_24h") if isinstance(status.get("exchange_snapshot_24h"), dict) else {}
    snapshot = {
        "ts_utc": now.isoformat(),
        "scheduler_ready": _task_is_ready(),
        "kill_switch_on": STOP_FILE.exists(),
        "heartbeat_age_min": hb_age,
        "status_running": status.get("running"),
        "status_restart_count": status.get("restart_count"),
        "status_error_count": status.get("error_count"),
        "status_symbol": status.get("symbol"),
        "status_testnet": status.get("testnet"),
        "status_enable_trading": status.get("enable_trading"),
        "exchange_snapshot_24h_available": exchange_24h.get("available"),
        "exchange_snapshot_24h_fills_count": exchange_24h.get("fills_count"),
        "exchange_snapshot_24h_realized_pnl": exchange_24h.get("realized_pnl"),
        "exchange_snapshot_24h_commission": exchange_24h.get("commission"),
        "exchange_snapshot_24h_funding_fee": exchange_24h.get("funding_fee"),
        "exchange_snapshot_24h_net": exchange_24h.get("net"),
        "risk_profile_pipeline": _risk_profile_pipeline_status(status),
        "mkm_singular_core": (
            _extract_singular_core_kpi(trader_state)
            if isinstance(trader_state, dict) and trader_state.get("signal_total_count") is not None
            else (
                status.get("mkm_singular_core")
                if isinstance(status.get("mkm_singular_core"), dict)
                else _extract_singular_core_kpi(trader_state)
            )
        ),
        "logos_timeline": _logos_timeline_status(),
        "watchdog": _watchdog_counters(log_text),
        "dual_regime_state_kpi": _extract_dual_regime_state_kpi(status, trader_state),
    }

    day = now.strftime("%Y%m%d")
    jsonl_path = KPI_DIR / f"kpi_snapshot_{day}.jsonl"
    latest_path = KPI_DIR / "latest_kpi.json"

    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")

    latest_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
