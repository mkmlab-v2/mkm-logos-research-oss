#!/usr/bin/env python3
"""Run GraphRAG B-track sweeps in parallel (logos subset, per-case, wire+semantic)."""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_graphrag_parallel_tracks_v1.json"

TRACKS = (
    ("logos_subset", ROOT / "scripts" / "comp_graphrag_logos_subset_sweep_v1.py"),
    ("per_case", ROOT / "scripts" / "comp_graphrag_per_case_sweep_v1.py"),
    ("wire_semantic", ROOT / "scripts" / "comp_graphrag_wire_semantic_sweep_v1.py"),
)


def _utc() -> str:
    from datetime import timezone as tz

    return datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_track(name: str, script: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout_tail = (proc.stdout or "").strip()[-800:]
    stderr_tail = (proc.stderr or "").strip()[-400:]
    return {
        "track": name,
        "script": str(script.relative_to(ROOT)).replace("\\", "/"),
        "exit_code": proc.returncode,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    max_exit = 0
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_run_track, name, path): name for name, path in TRACKS}
        for fut in as_completed(futures):
            row = fut.result()
            results.append(row)
            max_exit = max(max_exit, int(row["exit_code"]))

    results.sort(key=lambda r: r["track"])
    doc = {
        "schema": "comp_graphrag_parallel_tracks_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_research_only",
        "active_report_untouched": True,
        "tracks": results,
        "artifacts": {
            "logos_subset": "reports/constitution/btrack_pilot/comp_graphrag_logos_subset_sweep_v1.json",
            "per_case": "reports/constitution/btrack_pilot/comp_graphrag_per_case_sweep_v1.json",
            "wire_semantic": "reports/constitution/btrack_pilot/comp_graphrag_wire_semantic_sweep_v1.json",
            "prior_full_sweep": "reports/constitution/btrack_pilot/comp_graphrag_philosophy_sweep_v1.json",
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "tracks": results}, ensure_ascii=False))
    return max_exit


if __name__ == "__main__":
    raise SystemExit(main())
