#!/usr/bin/env python3
"""Gate: clinic LOI Figma reverse-sync (local map + optional live Figma)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "scripts/sync_clinic_loi_figma_design_tokens_v1.py"
PACK = ROOT / "scripts/build_clinic_loi_figma_reverse_sync_pack_v1.py"
CAPTURE = ROOT / "scripts/capture_clinic_loi_figma_reference_playwright_v1.mjs"
MKM_LIFE = ROOT / "projects/mkm/mkm-life"
DEFAULT_OUT = ROOT / "reports/clinic_loi_figma_reverse_sync_gate_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fetch-figma", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []

    proc = subprocess.run([sys.executable, str(PACK)], cwd=str(ROOT), capture_output=True, text=True)
    steps.append({"step": "pack", "exit_code": proc.returncode, "ok": proc.returncode == 0})
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)

    sync_cmd = [sys.executable, str(SYNC)]
    if args.fetch_figma:
        sync_cmd.append("--fetch-figma")
    proc = subprocess.run(sync_cmd, cwd=str(ROOT), capture_output=True, text=True)
    steps.append({"step": "sync", "exit_code": proc.returncode, "ok": proc.returncode == 0})

    import os

    env = os.environ.copy()
    env["MKM_WORKSPACE_ROOT"] = str(ROOT)
    proc = subprocess.run(
        ["node", str(CAPTURE)],
        cwd=str(MKM_LIFE),
        capture_output=True,
        text=True,
        env=env,
    )
    steps.append({"step": "reference_capture", "exit_code": proc.returncode, "ok": proc.returncode == 0})

    sync_report = {}
    sync_path = ROOT / "reports/clinic_loi_figma_design_sync_v1_latest.json"
    if sync_path.is_file():
        sync_report = json.loads(sync_path.read_text(encoding="utf-8-sig"))

    capture_report = {}
    cap_path = ROOT / "reports/clinic_loi_figma_reference_capture_v1_latest.json"
    if cap_path.is_file():
        capture_report = json.loads(cap_path.read_text(encoding="utf-8-sig"))

    ok = all(s["ok"] for s in steps) and sync_report.get("ok") is True

    # Refresh pack after sync + capture so optional artifacts are included.
    if ok:
        subprocess.run([sys.executable, str(PACK)], cwd=str(ROOT), check=False)

    report = {
        "schema": "clinic_loi_figma_reverse_sync_gate_v1",
        "ok": ok,
        "decision": "PASS" if ok else "FAIL",
        "send_gate": "HOLD",
        "lane_status": "frozen_deferred",
        "steps": steps,
        "sync_report": sync_report,
        "capture_report": capture_report,
        "reproduce": "powershell -File scripts/Run-ClinicLoiFigmaReverseSyncAuto_v1.ps1",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "decision": report["decision"], "out": str(args.out)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
