#!/usr/bin/env python3
"""COMP-ATOM-05 parallel full: 40-case sweep + compare + v2 pytest."""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_atom05_parallel_full_v1.json"


def _utc() -> str:
    from datetime import timezone as tz

    return datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_py(script_rel: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / script_rel)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "track": script_rel,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").strip()[-700:],
        "stderr_tail": (proc.stderr or "").strip()[-300:],
    }


def _run_pytest(path: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", path, "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "track": path,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").strip()[-400:],
        "stderr_tail": (proc.stderr or "").strip()[-300:],
    }


def _job_full_sweep() -> dict:
    return _run_py("scripts/comp_atom05_full_v2_sweep_v1.py")


def _job_compare() -> dict:
    return _run_py("scripts/comp_atom05_compare_prior_v1.py")


def _job_v2_test() -> dict:
    return _run_pytest("tests/test_v2_graph_wire_selective_bridge_v1.py")


def _job_atom05_tests() -> dict:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_mkm_graph_wire_bridge_influence_v1.py",
            "tests/test_comp_atom05_graph_wire_bridge_smoke_v1.py",
            "-q",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "track": "tests/comp_atom05_bundle",
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").strip()[-400:],
        "stderr_tail": (proc.stderr or "").strip()[-300:],
    }


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("full_v2_sweep", _job_full_sweep),
        ("compare_prior", _job_compare),
        ("v2_api_test", _job_v2_test),
        ("atom05_pytest", _job_atom05_tests),
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

    if any(r["job"] == "full_v2_sweep" and r["exit_code"] == 0 for r in results):
        cmp_row = next((r for r in results if r["job"] == "compare_prior"), None)
        if cmp_row and cmp_row["exit_code"] != 0:
            retry = _run_py("scripts/comp_atom05_compare_prior_v1.py")
            retry["job"] = "compare_prior_retry"
            results.append(retry)
            max_exit = max(max_exit, int(retry["exit_code"]))

    results.sort(key=lambda r: r.get("job", ""))
    doc = {
        "schema": "comp_atom05_parallel_full_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "tracks": results,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "tracks": results}, ensure_ascii=False))
    return max_exit


if __name__ == "__main__":
    raise SystemExit(main())
