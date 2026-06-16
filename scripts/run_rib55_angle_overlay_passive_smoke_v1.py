#!/usr/bin/env python3
"""[HYPO] Passive smoke: rib55 manifest render + pytest (non-gating)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/rib55_angle_overlay_passive_smoke_v1_latest.json"
ART = ROOT / "docs/final/artifacts/rib55_angle_overlay_passive_smoke_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    steps: list[dict] = []
    render = subprocess.run(
        [sys.executable, "scripts/render_rib55_angle_overlay_v1.py", "--update-manifest"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    steps.append(
        {
            "step": "render",
            "exit_code": render.returncode,
            "stdout_tail": (render.stdout or "")[-400:],
        }
    )
    if render.returncode != 0:
        doc = {
            "schema": "rib55_angle_overlay_passive_smoke_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "send_gate": "HOLD",
            "steps": steps,
            "ok": False,
        }
        payload = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        OUT.write_text(payload, encoding="utf-8")
        ART.write_text(payload, encoding="utf-8")
        return 1

    test = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_render_rib55_angle_overlay_v1.py", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    steps.append(
        {
            "step": "pytest",
            "exit_code": test.returncode,
            "stdout_tail": (test.stdout or "")[-400:],
        }
    )
    ok = test.returncode == 0
    doc = {
        "schema": "rib55_angle_overlay_passive_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "adjudication": "pending",
        "steps": steps,
        "ok": ok,
        "reproduce": "py scripts/run_rib55_angle_overlay_passive_smoke_v1.py",
    }
    payload = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ART.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    ART.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(ART)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
