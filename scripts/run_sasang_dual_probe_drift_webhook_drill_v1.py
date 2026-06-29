#!/usr/bin/env python3
"""Dual-probe drift webhook drill — dry-run default; optional --live POST [HYPO]."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/sasang_dual_probe_drift_webhook_drill_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = [PY, str(ROOT / "scripts" / script)] + (extra or [])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true", help="POST webhook when URL configured")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("build_sasang_4agent_dual_probe_weekly_drift_alert_v1.py"))
    extra = ["--live"] if args.live else []
    steps.append(_run("build_sasang_4agent_dual_probe_drift_webhook_stub_v1.py", extra))

    webhook_url = (
        (os.getenv("SASANG_DUAL_PROBE_DRIFT_WEBHOOK_URL") or "").strip()
        or (os.getenv("OPS_ALARM_WEBHOOK_URL") or "").strip()
    )
    stub_path = ROOT / "reports/sasang_4agent_dual_probe_drift_webhook_stub_v1_latest.json"
    stub = json.loads(stub_path.read_text(encoding="utf-8-sig")) if stub_path.is_file() else {}

    drill_ok = all(s["ok"] for s in steps) and stub.get("stub_ok") is True
    doc = {
        "schema": "sasang_dual_probe_drift_webhook_drill_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "live_mode": args.live,
        "webhook_configured": bool(webhook_url),
        "webhook_env_keys": [
            "SASANG_DUAL_PROBE_DRIFT_WEBHOOK_URL",
            "OPS_ALARM_WEBHOOK_URL",
        ],
        "steps": steps,
        "drill_ok": drill_ok,
        "webhook_post_status": stub.get("webhook_post_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_dual_probe_drift_webhook_drill_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": drill_ok, "live_mode": args.live, "webhook_post_status": doc["webhook_post_status"]}))
    return 0 if drill_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
