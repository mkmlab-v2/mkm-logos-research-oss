#!/usr/bin/env python3
"""Phase 5 [HYPO]: drill-down shard bundle + hero rebuild + pytest."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/magic_orb_drilldown_shard_phase5_chain_v1_latest.json"
INDEX = ROOT / "docs/final/artifacts/magic_orb_drilldown_shards_v1_latest.json"
HERO_BUILD = ROOT / "scripts/build_magic_orb_hero_slices_bundle_v1.py"
DRILL_BUILD = ROOT / "scripts/build_magic_orb_drilldown_shard_bundle_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    report: dict = {
        "schema": "magic_orb_drilldown_shard_phase5_chain_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "steps": [],
        "ok": False,
    }

    def run_step(name: str, cmd: list[str]) -> bool:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        report["steps"].append(
            {
                "name": name,
                "cmd": " ".join(cmd),
                "exit_code": proc.returncode,
                "stdout": proc.stdout.strip()[:2000],
                "stderr": proc.stderr.strip()[:500],
            }
        )
        return proc.returncode == 0

    ok = run_step(
        "rebuild_hero_slices",
        [sys.executable, str(HERO_BUILD), "--sync-mkmlife"],
    )
    ok = run_step(
        "build_drilldown_shards",
        [sys.executable, str(DRILL_BUILD), "--sync-mkmlife"],
    ) and ok
    ok = run_step(
        "pytest_drilldown",
        [sys.executable, "-m", "pytest", "tests/test_magic_orb_drilldown_shard_phase5_v1.py", "-q"],
    ) and ok

    if INDEX.is_file():
        idx = json.loads(INDEX.read_text(encoding="utf-8-sig"))
        report["slice_count"] = len(idx.get("slices") or [])
        report["slices"] = [s.get("summary") for s in idx.get("slices") or []]

    report["ok"] = ok
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "report": str(OUT.relative_to(ROOT)).replace("\\", "/")}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
