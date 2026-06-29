#!/usr/bin/env python3
"""Phase 1: hero slices bundle (passion + Dan.2 + chronology) → validate → mkmlife sync."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_magic_orb_hero_slices_bundle_v1.py"
OUT = ROOT / "reports/bible_topology_hero_phase1_chain_v1_latest.json"
BUNDLE = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    report: dict = {
        "schema": "bible_topology_hero_phase1_chain_v1",
        "generated_at_utc": _utc(),
        "steps": [],
        "ok": False,
    }

    def run_step(name: str, cmd: list[str]) -> bool:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        step = {
            "name": name,
            "cmd": " ".join(cmd),
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip()[:2000],
            "stderr": proc.stderr.strip()[:500],
        }
        report["steps"].append(step)
        return proc.returncode == 0

    ok = run_step(
        "build_hero_slices",
        [sys.executable, str(BUILD), "--sync-mkmlife"],
    )
    ok = run_step(
        "pytest",
        [sys.executable, "-m", "pytest", "tests/test_build_magic_orb_hero_slices_bundle_v1.py", "-q"],
    ) and ok

    if BUNDLE.is_file():
        doc = json.loads(BUNDLE.read_text(encoding="utf-8-sig"))
        report["slice_count"] = len(doc.get("slices") or [])
        report["era_count"] = len((doc.get("chronology") or {}).get("eras") or [])
        report["default_slice_id"] = doc.get("default_slice_id")

    report["ok"] = ok
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "slices": report.get("slice_count"),
                "eras": report.get("era_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
