#!/usr/bin/env python3
"""Checker — BESD DPT-R v2 bounded loader artifact."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/research/besd/dpt_r_fixture_validation/BESD_DPT_R_V2_BOUNDED_LOADER_RESULTS_V1.json"
LOADER = ROOT / "scripts/run_besd_dpt_r_v2_bounded_loader_v1.py"
CHECK = ROOT / "docs/final/artifacts/besd_dpt_r_v2_bounded_loader_check_v1_latest.json"


def main() -> int:
    checks: list[dict] = []
    if not OUT.is_file():
        rc = subprocess.call([sys.executable, str(LOADER)], cwd=ROOT)
        if rc != 0:
            checks.append({"ok": False, "code": "LOADER_RUN_FAIL", "exit": rc})
            CHECK.parent.mkdir(parents=True, exist_ok=True)
            CHECK.write_text(json.dumps({"ok": False, "checks": checks}, indent=2), encoding="utf-8")
            return 2

    doc = json.loads(OUT.read_text(encoding="utf-8"))
    bl = doc.get("bounded_loader") or {}
    src = LOADER.read_text(encoding="utf-8")

    for code, cond in (
        ("DUAL_LABEL", bl.get("dual_label_record_present") is True),
        ("FAIL_CLOSED", bl.get("fail_closed_tokens_present") is True),
        ("LOADER_COMPATIBLE", bl.get("LOADER_COMPATIBLE") is True),
        ("V1_UNMUTATED", bl.get("v1_loader_unmutated") is True),
        ("TOKENS_IN_SOURCE", "MISSING_BRIDGE_ENTRY" in src and "BRIDGE_HASH_MISMATCH" in src),
        ("DECIDE_PASS", doc.get("DECIDE_ONE") == "BESD_DPT_R_V2_BOUNDED_LOADER_PASS"),
    ):
        checks.append({"ok": cond, "code": code})

    ok = all(c["ok"] for c in checks)
    CHECK.parent.mkdir(parents=True, exist_ok=True)
    CHECK.write_text(
        json.dumps({"ok": ok, "checks": checks, "artifact": str(OUT)}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": ok, "failed": [c for c in checks if not c["ok"]]}))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
