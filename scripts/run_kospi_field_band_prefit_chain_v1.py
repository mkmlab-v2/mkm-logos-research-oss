#!/usr/bin/env python3
"""Chain: prefit panel → tune freeze → prophecy-only honest OOS [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return {"step": name, "exit_code": cp.returncode, "tail": ((cp.stdout or "") + (cp.stderr or "")).strip()[-500:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    args = ap.parse_args()

    steps = [
        _run("prophecy_only_panel", [PY, "scripts/build_kospi_prophecy_only_panel_v1.py"]),
        _run("prefit_panel", [PY, "scripts/build_kospi_field_band_prefit_panel_v1.py"]),
        _run("prefit_tune", [PY, "scripts/run_kospi_field_band_prefit_tune_v1.py"]),
        _run("prefit_frozen_oos", [PY, "scripts/run_kospi_field_band_prefit_frozen_oos_v1.py"]),
        _run("l4_prep", [PY, "scripts/build_kospi_field_band_l4_prep_packet_v1.py"]),
    ]
    ok = all(s["exit_code"] == 0 for s in steps)

    oos_path = ROOT / "reports/kospi_field_band_prefit_frozen_oos_v1_latest.json"
    oos: dict[str, Any] = {}
    if oos_path.is_file():
        try:
            oos = json.loads(oos_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            oos = {}

    completion = {
        "schema": "kospi_field_band_prefit_chain_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "steps": steps,
        "prefit_honest_oos_ready": oos.get("prefit_honest_oos_ready"),
        "comparison": oos.get("comparison"),
        "artifact": "reports/kospi_field_band_prefit_frozen_oos_v1_latest.json",
        "reproduce": "py scripts/run_kospi_field_band_prefit_chain_v1.py",
    }
    out = ROOT / "reports/kospi_field_band_prefit_chain_v1_latest.json"
    out.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": ok, "prefit_honest_oos_ready": oos.get("prefit_honest_oos_ready"), "comparison": oos.get("comparison")},
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
