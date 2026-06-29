#!/usr/bin/env python3
"""Read-only VPS health probe for B-track Phase-1 micro-live (Aroon overlay armed)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "btrack_phase1_micro_live_vps_health_v1"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "reports/btrack_phase1_micro_live_vps_health_v1_latest.json"
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
LOCAL_ENGINE_HANDOFF = (
    WORKSPACE_ROOT / "docs/final/artifacts/btc_limited_live_engine_input_from_btrack_typea_v1_latest.json"
)

OPERATING_MODE = {
    "label": "verified_current_drift_observed",
    "research_only": True,
    "hypothesis_tag": "[HYPO]",
    "notes": [
        "Overlay filters opposite-side entries; aligned wrong-direction entries are not blocked by guard.",
        "Pass means SSOT+health+sync baseline at probe time; not permanent wiring perfection.",
    ],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ssh(host: str, remote_cmd: str, *, timeout: int = 45) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["ssh", host, remote_cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _signal_key(doc: dict[str, Any]) -> str:
    sig = doc.get("btrack_signal") if isinstance(doc.get("btrack_signal"), dict) else {}
    side = str(sig.get("side_hint") or doc.get("side_hint") or "").upper()
    ev = str(sig.get("eval_date") or doc.get("eval_date") or "")
    return f"{side}|{ev}"


def _load_local_engine_handoff() -> dict[str, Any]:
    if not LOCAL_ENGINE_HANDOFF.is_file():
        return {}
    try:
        obj = json.loads(LOCAL_ENGINE_HANDOFF.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}
    return obj if isinstance(obj, dict) else {}


def probe_vps(
    *,
    vps_host: str,
    dest_root: str,
    pm2_app: str,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail[:500]})
        if not ok:
            blockers.append(f"{name}: {detail[:200]}")

    code, out, err = _ssh(vps_host, f"pm2 pid {pm2_app} 2>/dev/null")
    pm2_ok = code == 0 and out.strip().isdigit()
    pm2_status = "online" if pm2_ok else "unknown"
    if not pm2_ok and out.strip():
        pm2_status = out.strip()[:40]
    add("pm2_app_online", pm2_ok, f"app={pm2_app} status={pm2_status} pid={out.strip() or 'none'}")

    log_grep = (
        f"grep -h 'btrack_overlay=' /root/.pm2/logs/{pm2_app}-error.log 2>/dev/null | tail -n 1"
    )
    code2, log_line, _ = _ssh(vps_host, log_grep)
    overlay_log_ok = code2 == 0 and "btrack_overlay=True" in log_line
    add(
        "aroon_btrack_overlay_log",
        overlay_log_ok,
        log_line.strip() or err.strip() or "no btrack_overlay line",
    )

    state_path = f"{dest_root}/projects/bitcoin-trading/logs/trading_state.json"
    code3, state_raw, _ = _ssh(vps_host, f"cat {state_path} 2>/dev/null")
    overlay_state: dict[str, Any] = {}
    guard_state: dict[str, Any] = {}
    state: dict[str, Any] = {}
    state_ok = False
    if code3 == 0 and state_raw.strip():
        try:
            state = json.loads(state_raw)
            overlay_state = state.get("btrack_micro_live_overlay") if isinstance(state, dict) else {}
            if not isinstance(overlay_state, dict):
                overlay_state = {}
            state_ok = str(state.get("engine") or "") == "aroon_v1" and bool(overlay_state.get("active"))
        except json.JSONDecodeError:
            state_ok = False
    add(
        "trading_state_btrack_overlay",
        state_ok,
        json.dumps(overlay_state, ensure_ascii=False) if overlay_state else "missing_or_inactive",
    )

    guard_state = state.get("btrack_micro_live_guard") if isinstance(state, dict) else {}
    guard_ok = isinstance(guard_state, dict) and "entries_today" in guard_state
    if state_ok and guard_ok:
        guard_ok = bool(guard_state.get("active"))
    add(
        "trading_state_policy_guard",
        guard_ok,
        json.dumps(guard_state, ensure_ascii=False) if guard_state else "missing",
    )

    engine_path = (
        f"{dest_root}/docs/final/artifacts/btc_limited_live_engine_input_from_btrack_typea_v1_latest.json"
    )
    code4, engine_raw, _ = _ssh(vps_host, f"cat {engine_path} 2>/dev/null")
    engine_doc: dict[str, Any] = {}
    engine_ok = False
    if code4 == 0 and engine_raw.strip():
        try:
            engine_doc = json.loads(engine_raw)
            engine_ok = str(engine_doc.get("status") or "").upper() == "READY_FOR_ENGINE_SUBMIT"
        except json.JSONDecodeError:
            engine_ok = False
    sig = engine_doc.get("btrack_signal") if isinstance(engine_doc.get("btrack_signal"), dict) else {}
    add(
        "remote_engine_handoff",
        engine_ok,
        f"status={engine_doc.get('status')} side={sig.get('side_hint')} eval={sig.get('eval_date')}",
    )

    ws = workspace_root or WORKSPACE_ROOT
    local_engine = _load_local_engine_handoff()
    if not local_engine and ws != WORKSPACE_ROOT:
        alt = ws / "docs/final/artifacts/btc_limited_live_engine_input_from_btrack_typea_v1_latest.json"
        if alt.is_file():
            try:
                local_engine = json.loads(alt.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, OSError):
                local_engine = {}
    local_sig = _signal_key(local_engine) if local_engine else ""
    remote_sig = _signal_key(engine_doc) if engine_doc else ""
    overlay_sig = ""
    if overlay_state.get("active"):
        overlay_sig = f"{str(overlay_state.get('side_hint') or '').upper()}|{overlay_state.get('eval_date') or ''}"
    drift_ok = True
    drift_detail = "no_local_handoff"
    if local_sig:
        drift_ok = local_sig == remote_sig
        drift_detail = f"local={local_sig} remote={remote_sig}"
        if overlay_sig and overlay_sig != remote_sig:
            drift_ok = False
            drift_detail += f" overlay_runtime={overlay_sig}"
    add("local_remote_signal_drift", drift_ok, drift_detail)

    healthy = pm2_ok and (overlay_log_ok or state_ok) and engine_ok and guard_ok and drift_ok
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "operating_mode": OPERATING_MODE,
        "vps_host": vps_host,
        "dest_root": dest_root,
        "pm2_app": pm2_app,
        "vps_micro_live_healthy": bool(healthy),
        "pm2_status": pm2_status,
        "overlay_from_trading_state": overlay_state,
        "remote_engine_handoff": {
            "status": engine_doc.get("status"),
            "side_hint": sig.get("side_hint"),
            "eval_date": sig.get("eval_date"),
        },
        "drift_observation": {
            "local_signal_key": local_sig or None,
            "remote_signal_key": remote_sig or None,
            "runtime_overlay_key": overlay_sig or None,
            "drift_detected": not drift_ok,
        },
        "checks": checks,
        "blockers": blockers,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vps-host", default="vps-mkmlife")
    ap.add_argument("--dest-root", default="/opt/mkm-destiny-ai-41e38ec6")
    ap.add_argument("--pm2-app", default="bitcoin-live-small-24h")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    doc = probe_vps(
        vps_host=args.vps_host,
        dest_root=args.dest_root,
        pm2_app=args.pm2_app,
        workspace_root=args.workspace_root,
    )
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"WROTE: {args.out}")
        print(f"vps_micro_live_healthy={doc.get('vps_micro_live_healthy')}")

    if args.strict and not doc.get("vps_micro_live_healthy"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
