#!/usr/bin/env python3
"""Parallel: anchor07 wire source AB + handoff + pytest + per-case delta."""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/constitution/btrack_pilot/comp_atom05_parallel_fuse_v3.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_script(rel: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / rel)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "track": rel,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").strip()[-500:],
        "stderr_tail": (proc.stderr or "").strip()[-250:],
    }


def _run_pytest(paths: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "track": " ".join(paths),
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").strip()[-400:],
        "stderr_tail": (proc.stderr or "").strip()[-200:],
    }


def _job_anchor07_ab() -> dict:
    return _run_script("scripts/comp_anchor07_wire_source_ab_v1.py")


def _job_handoff() -> dict:
    return _run_script("scripts/comp_compression_lane_handoff_v1.py")


def _job_per_case_delta() -> dict:
    return _run_script("scripts/comp_atom05_bridge_boost_per_case_delta_v1.py")


def _job_pytest_wire() -> dict:
    return _run_pytest(
        [
            "tests/test_mkm_graph_wire_bridge_influence_v1.py",
            "tests/test_compression_profile_v1.py",
            "tests/test_v2_graph_wire_selective_bridge_v1.py",
        ]
    )


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("anchor07_wire_ab", _job_anchor07_ab),
        ("handoff", _job_handoff),
        ("per_case_delta", _job_per_case_delta),
        ("pytest_wire_stack", _job_pytest_wire),
    ]
    results: list[dict] = []
    max_exit = 0
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fn): name for name, fn in jobs}
        for fut in as_completed(futures):
            name = futures[fut]
            row = fut.result()
            row["job"] = name
            results.append(row)
            max_exit = max(max_exit, int(row["exit_code"]))

    results.sort(key=lambda r: r.get("job", ""))
    doc = {
        "schema": "comp_atom05_parallel_fuse_v3",
        "generated_at_utc": _utc(),
        "tracks": results,
        "artifacts": {
            "anchor07_ab": "reports/constitution/btrack_pilot/comp_anchor07_wire_source_ab_v1.json",
            "handoff": "reports/constitution/btrack_pilot/comp_compression_lane_handoff_v1.json",
            "per_case_delta": "reports/constitution/btrack_pilot/comp_atom05_bridge_boost_per_case_delta_v1.json",
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "tracks": results}, ensure_ascii=False))
    return max_exit


if __name__ == "__main__":
    raise SystemExit(main())
