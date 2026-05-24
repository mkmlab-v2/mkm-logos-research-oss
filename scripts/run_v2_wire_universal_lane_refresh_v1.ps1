#!/usr/bin/env python3
"""Refresh all Universal Matrix wire AB lane artifacts (B-track; active untouched)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANES = ("finance", "enterprise", "ijeoma", "ijeoma_chunk")
OUT = ROOT / "reports/constitution/btrack_pilot/comp_v2_universal_wire_lane_refresh_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    results: list[dict] = []
    failed = False
    for lane in LANES:
        script = ROOT / "scripts/run_universal_compression_bench_wire_ab_lane_v1.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--lane", lane],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        row = {"lane": lane, "exit_code": proc.returncode, "stdout": (proc.stdout or "").strip()[-800:]}
        results.append(row)
        if proc.returncode != 0:
            failed = True
    doc = {
        "schema": "comp_v2_universal_wire_lane_refresh_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "lanes": results,
        "artifacts": [
            "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_finance_v1.json",
            "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_enterprise_v1.json",
            "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_ijeoma_v1.json",
            "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_ijeoma_chunk_v1.json",
        ],
        "ok": not failed,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "ok": doc["ok"]}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
