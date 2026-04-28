#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointerguard_p0_alert_drill_latest.json"
HISTORY_DEFAULT = ART / "pointerguard_p0_alert_drill_history_v1.jsonl"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {"cmd": cmd, "exit_code": cp.returncode, "stdout": cp.stdout.strip(), "stderr": cp.stderr.strip()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--simulate-reasons",
        type=str,
        default="guard_applied,unauthorized_pattern_detected",
        help="Comma-separated P0 reasons for drill payload.",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--alert-on-failure", action="store_true", help="If drill check fails, send a real P0 failure alert.")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--history-jsonl", type=Path, default=HISTORY_DEFAULT)
    args = ap.parse_args()

    py = sys.executable
    cmd = [py, "scripts/send_pointerguard_ops_alert_v1.py", "--simulate", args.simulate_reasons]
    if args.dry_run:
        cmd.append("--dry-run")
    result = _run(cmd)
    delivery_path = ART / "pointerguard_ops_alert_delivery_latest.json"
    delivery = _read_json(delivery_path) if delivery_path.exists() else {}
    status = str(delivery.get("delivery", {}).get("status", "unknown"))
    should_send = bool(delivery.get("alert", {}).get("should_send", False))
    severity = str(delivery.get("alert", {}).get("severity", "UNKNOWN"))
    ok = result["exit_code"] == 0 and should_send and severity == "P0"
    failure_alert_result: dict[str, Any] | None = None
    if (not ok) and bool(args.alert_on_failure):
        fail_cmd = [py, "scripts/send_pointerguard_ops_alert_v1.py", "--simulate", "p0_drill_failed"]
        failure_alert_result = _run(fail_cmd)

    out_doc = {
        "schema": "pointerguard_p0_alert_drill_v1",
        "generated_at_utc": _now_utc(),
        "input": {"simulate_reasons": [s.strip() for s in args.simulate_reasons.split(",") if s.strip()], "dry_run": bool(args.dry_run)},
        "command_result": result,
        "delivery_snapshot": {
            "path": str(delivery_path),
            "status": status,
            "should_send": should_send,
            "severity": severity,
            "webhook_configured": bool(delivery.get("delivery", {}).get("webhook_configured", False)),
            "sent": bool(delivery.get("delivery", {}).get("sent", False)),
        },
        "failure_alert_result": failure_alert_result,
        "ok": ok,
    }
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    history_path = args.history_jsonl if args.history_jsonl.is_absolute() else ROOT / args.history_jsonl
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_row = {
        "generated_at_utc": out_doc["generated_at_utc"],
        "dry_run": bool(args.dry_run),
        "ok": ok,
        "delivery_status": status,
        "severity": severity,
        "should_send": should_send,
    }
    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(history_row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": ok, "out": str(out_path), "delivery_status": status}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
