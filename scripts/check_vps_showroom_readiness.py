#!/usr/bin/env python3
"""Evaluate local readiness for VPS 24h daemon + public showroom pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "vps_24h_daemon_showroom_readiness_latest.json"


def _exists(path: Path) -> bool:
    return path.exists()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    required_paths = {
        "daemon_main": ROOT / "projects" / "bitcoin-trading" / "src" / "daemon" / "bitcoin_trading_daemon.py",
        "daemon_start_24h": ROOT / "projects" / "bitcoin-trading" / "scripts" / "start_24h_daemon.py",
        "daemon_ensure": ROOT / "projects" / "bitcoin-trading" / "ops" / "windows-rehearsal" / "ensure_daemon_running.ps1",
        "gateway_py": ROOT / "projects" / "bitcoin-trading" / "ops" / "windows-rehearsal" / "jemaai-cloud-mvp" / "public_event_gateway.py",
        "gateway_nginx_example": ROOT
        / "projects"
        / "bitcoin-trading"
        / "ops"
        / "windows-rehearsal"
        / "jemaai-cloud-mvp"
        / "nginx_public_event_gateway.conf.example",
        "showroom_poll_html": ROOT
        / "projects"
        / "bitcoin-trading"
        / "ops"
        / "windows-rehearsal"
        / "jemaai-cloud-mvp"
        / "public_showroom_poll.html",
        "n8n_whitelist_function": ROOT
        / "projects"
        / "bitcoin-trading"
        / "ops"
        / "windows-rehearsal"
        / "jemaai-cloud-mvp"
        / "examples"
        / "n8n_public_event_whitelist_function.js",
        "e2e_smoke_script": ROOT / "projects" / "bitcoin-trading" / "ops" / "windows-rehearsal" / "run_jemaai_public_event_e2e_smoke.ps1",
        "ingest_minimal_example": ROOT
        / "projects"
        / "bitcoin-trading"
        / "ops"
        / "windows-rehearsal"
        / "jemaai-cloud-mvp"
        / "examples"
        / "public_event_ingest_minimal.v1.json",
    }

    checks: Dict[str, bool] = {k: _exists(v) for k, v in required_paths.items()}
    failed_reasons: List[str] = [f"missing:{k}:{v}" for k, v in required_paths.items() if not checks[k]]

    trading_state_primary = ROOT / "projects" / "bitcoin-trading" / "logs" / "trading_state.json"
    trading_state_fallback = ROOT / "projects" / "bitcoin-trading" / "memory" / "trading_daemon_status.json"
    primary_doc = _read_json(trading_state_primary)
    fallback_doc = _read_json(trading_state_fallback)

    state_doc = primary_doc
    trading_state_source = str(trading_state_primary)
    if not state_doc and fallback_doc:
        state_doc = fallback_doc
        trading_state_source = str(trading_state_fallback)

    daemon_running = bool(state_doc.get("running")) if state_doc else False
    enable_trading = bool(state_doc.get("enable_trading")) if state_doc else False
    # Prefer fallback runtime when primary says "not running" but watchdog mirror indicates active lock/runtime.
    if (
        primary_doc
        and fallback_doc
        and not daemon_running
        and bool(fallback_doc.get("running"))
    ):
        state_doc = fallback_doc
        daemon_running = True
        enable_trading = bool(fallback_doc.get("enable_trading"))
        trading_state_source = str(trading_state_fallback)
    checks["trading_state_exists"] = trading_state_primary.exists() or trading_state_fallback.exists()
    checks["daemon_running_flag"] = daemon_running
    checks["enable_trading_flag"] = enable_trading
    if not checks["trading_state_exists"]:
        failed_reasons.append(f"missing:trading_state:{trading_state_primary}|{trading_state_fallback}")

    # Readiness scoring by lane.
    core_files_ready = all(checks[k] for k in required_paths.keys())
    public_lane_ready = all(
        checks[k]
        for k in (
            "gateway_py",
            "gateway_nginx_example",
            "showroom_poll_html",
            "n8n_whitelist_function",
            "ingest_minimal_example",
            "e2e_smoke_script",
        )
    )
    private_lane_ready = all(
        checks[k] for k in ("daemon_main", "daemon_start_24h", "daemon_ensure", "trading_state_exists")
    )

    overall = core_files_ready and public_lane_ready and private_lane_ready

    payload: Dict[str, Any] = {
        "schema": "vps_24h_daemon_showroom_readiness_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "paths": {k: str(v) for k, v in required_paths.items()},
        "checks": checks,
        "lane_status": {
            "private_trading_lane_ready": private_lane_ready,
            "public_showroom_lane_ready": public_lane_ready,
        },
        "runtime_snapshot": {
            "trading_state_path": trading_state_source,
            "trading_state_running": daemon_running,
            "trading_state_enable_trading": enable_trading,
        },
        "result": {
            "overall_ready": overall,
            "go_no_go": "GO" if overall else "NO_GO",
            "failed_reasons": failed_reasons,
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"go_no_go: {payload['result']['go_no_go']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

