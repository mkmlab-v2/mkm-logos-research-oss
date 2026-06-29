#!/usr/bin/env python3
"""Smoke frozen Edge Encoder exe when binary_built [HYPO] B-track."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "docs/final/artifacts/edge_encoder_pyinstaller_readiness_v1_latest.json"
REPORT = ROOT / "reports/edge_encoder_pyinstaller_binary_smoke_v1_latest.json"


def main() -> int:
    if not READINESS.is_file():
        print(json.dumps({"ok": False, "error": "missing readiness artifact"}, ensure_ascii=False))
        return 1
    doc = json.loads(READINESS.read_text(encoding="utf-8"))
    status = str(doc.get("status") or "")
    exe_rel = doc.get("exe_path")
    if status != "binary_built" or not exe_rel:
        out = {
            "ok": True,
            "skipped": True,
            "reason": status or "no exe",
            "note": "Install PyInstaller and run build_edge_encoder_sdk_pyinstaller_v1.py --build",
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(out, ensure_ascii=False))
        return 0

    exe = (ROOT / exe_rel).resolve()
    if not exe.is_file():
        print(json.dumps({"ok": False, "error": f"missing exe {exe}"}, ensure_ascii=False))
        return 1

    proc = subprocess.run(
        [str(exe), "encode-manifest", "--entry-id", "pilot_ninth_rib_55deg_v0"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = {
        "ok": proc.returncode == 0,
        "exe": str(exe.relative_to(ROOT)).replace("\\", "/"),
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-400:],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": out["ok"], "returncode": proc.returncode}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
