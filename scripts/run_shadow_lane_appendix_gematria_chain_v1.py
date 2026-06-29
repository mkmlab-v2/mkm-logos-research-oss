#!/usr/bin/env python3
"""P1 chain: shadow appendix gematria + canon xref + isolation gate [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT_DEFAULT = ROOT / "reports/shadow_lane_appendix_gematria_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, script: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run([PY, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    steps = [
        _run("appendix_gematria", "build_shadow_lane_appendix_gematria_v1.py"),
        _run("canon_xref_map", "build_shadow_canon_gematria_xref_map_v1.py"),
        _run("isolation_gate", "build_shadow_lane_gematria_gate_v1.py"),
    ]
    if not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [PY, "-m", "pytest", "tests/test_shadow_lane_appendix_gematria_v1.py", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest",
                "script": "tests/test_shadow_lane_appendix_gematria_v1.py",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-300:],
                "stderr_tail": (proc.stderr or "")[-200:],
                "ok": proc.returncode == 0,
            }
        )

    gate_path = ROOT / "docs/final/artifacts/shadow_lane_gematria_gate_v1_latest.json"
    gate = {}
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    all_ok = all(s["ok"] for s in steps) and gate.get("gate_ok") is True
    doc = {
        "schema": "shadow_lane_appendix_gematria_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "gate_ok": gate.get("gate_ok"),
        "ok": all_ok,
        "reproduce": "py scripts/run_shadow_lane_appendix_gematria_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "gate_ok": gate.get("gate_ok")}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
