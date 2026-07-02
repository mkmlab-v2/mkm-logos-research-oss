#!/usr/bin/env python3
"""Logos inquiry PayApp E2E smoke v1 — scaffold dry-run (P0-2 · no live charge without G12)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from core.logos_inquiry_payapp_e2e_v1 import validate_scaffold  # noqa: E402

OUT = ROOT / "reports/logos_inquiry_payapp_e2e_smoke_v1_latest.json"
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-handoff", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_handoff:
        proc = subprocess.run(
            [PY, str(ROOT / "scripts/build_logos_jema_ai_research_handoff_v1.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append({"name": "rebuild_handoff", "ok": proc.returncode == 0, "exit_code": proc.returncode})

    report = validate_scaffold(root=ROOT)
    report["generated_at_utc"] = _utc()
    report["steps"] = steps

    handoff_path = ROOT / "projects/no1kmedi/public/data/logos_jema_ai_research_handoff_v1.json"
    if handoff_path.is_file():
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        billing = handoff.get("billing") or {}
        report["handoff_billing_ok"] = bool(billing.get("payapp_e2e_contract"))
        report["ok"] = report["ok"] and report["handoff_billing_ok"]
    else:
        report["handoff_billing_ok"] = False
        report["ok"] = False

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_pytest:
        proc = subprocess.run(
            [PY, "-m", "pytest", "tests/test_logos_inquiry_payapp_e2e_v1.py", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        steps.append({"name": "pytest", "ok": proc.returncode == 0, "exit_code": proc.returncode})
        report["steps"] = steps
        report["ok"] = report["ok"] and proc.returncode == 0
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    no1k = ROOT / "projects/no1kmedi"
    http_proc = subprocess.run(
        ["npm", "run", "smoke:logos-inquiry-payapp-http"],
        cwd=no1k,
        capture_output=True,
        text=True,
        timeout=180,
        shell=True,
    )
    steps.append(
        {
            "name": "offline_http_chain",
            "ok": http_proc.returncode == 0,
            "exit_code": http_proc.returncode,
        }
    )
    report["steps"] = steps
    report["ok"] = report["ok"] and http_proc.returncode == 0
    http_out = ROOT / "reports/logos_inquiry_payapp_http_smoke_v1_latest.json"
    report["http_smoke_path"] = str(http_out) if http_out.is_file() else None
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": report["ok"], "out": str(OUT), "mode": report["mode"]}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
