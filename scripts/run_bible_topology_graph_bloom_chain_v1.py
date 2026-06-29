#!/usr/bin/env python3
"""One-click: bible topology passion shard → graph bloom → validate → mkmlife POC sync."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_bible_topology_graph_bloom_v1.py"
OUT = ROOT / "reports/bible_topology_graph_bloom_chain_v1_latest.json"
PASSION_ARTIFACT = ROOT / "docs/final/artifacts/magic_orb_graph_bloom_bible_topology_passion_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    report: dict = {
        "schema": "bible_topology_graph_bloom_chain_v1",
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
        "build",
        [
            sys.executable,
            str(BUILD),
            "--promote-latest",
            "--sync-mkmlife",
        ],
    )
    ok = run_step(
        "pytest",
        [sys.executable, "-m", "pytest", "tests/test_build_bible_topology_graph_bloom_v1.py", "-q"],
    ) and ok

    if PASSION_ARTIFACT.is_file():
        doc = json.loads(PASSION_ARTIFACT.read_text(encoding="utf-8-sig"))
        report["nodes"] = doc.get("stats", {}).get("node_count")
        report["edges"] = doc.get("stats", {}).get("edge_count")
        report["slice_id"] = doc.get("source", {}).get("slice_id")

    report["ok"] = ok
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "nodes": report.get("nodes"), "edges": report.get("edges")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
