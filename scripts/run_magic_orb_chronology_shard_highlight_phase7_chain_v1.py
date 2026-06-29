#!/usr/bin/env python3
"""Phase 7 [HYPO]: chronology↔shard highlight map + phase6 refresh + pytest."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/magic_orb_chronology_shard_highlight_phase7_chain_v1_latest.json"
HIGHLIGHT = ROOT / "docs/final/artifacts/magic_orb_chronology_shard_highlight_v1_latest.json"
PHASE6_CHAIN = ROOT / "scripts/run_magic_orb_shard_explorer_phase6_chain_v1.py"
HIGHLIGHT_BUILD = ROOT / "scripts/build_magic_orb_chronology_shard_highlight_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    report: dict = {
        "schema": "magic_orb_chronology_shard_highlight_phase7_chain_v1",
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

    ok = run_step("refresh_phase6", [sys.executable, str(PHASE6_CHAIN)])
    ok = run_step(
        "build_chronology_highlight",
        [sys.executable, str(HIGHLIGHT_BUILD), "--sync-mkmlife"],
    ) and ok
    ok = run_step(
        "pytest_chronology_highlight",
        [sys.executable, "-m", "pytest", "tests/test_magic_orb_chronology_shard_highlight_phase7_v1.py", "-q"],
    ) and ok

    if HIGHLIGHT.is_file():
        doc = json.loads(HIGHLIGHT.read_text(encoding="utf-8-sig"))
        report["entry_count"] = len(doc.get("entries") or [])
        report["with_shard_extra"] = sum(
            1 for e in doc.get("entries") or [] if int(e.get("shard_only_extra_hits") or 0) > 0
        )

    report["ok"] = ok
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "report": str(OUT.relative_to(ROOT)).replace("\\", "/")}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
