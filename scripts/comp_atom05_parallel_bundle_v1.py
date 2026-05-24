#!/usr/bin/env python3
"""Parallel: profile matrix sweep + compare refresh + atom05 pytest smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_atom05_parallel_bundle_v1.json"


def _utc() -> str:
    from datetime import timezone as tz

    return datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "track": script,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").strip()[-700:],
        "stderr_tail": (proc.stderr or "").strip()[-300:],
    }


def _pytest(paths: list[str]) -> dict:
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


def _job_matrix() -> dict:
    return _run("scripts/comp_atom05_profile_matrix_sweep_v1.py")


def _job_compare() -> dict:
    return _run("scripts/comp_atom05_compare_prior_v1.py")


def _job_pytest() -> dict:
    return _pytest(
        [
            "tests/test_mkm_graph_wire_bridge_influence_v1.py",
            "tests/test_comp_atom05_graph_wire_bridge_smoke_v1.py",
        ]
    )


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("profile_matrix", _job_matrix),
        ("compare_prior", _job_compare),
        ("pytest_smoke", _job_pytest),
    ]
    results: list[dict] = []
    max_exit = 0
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): name for name, fn in jobs}
        for fut in as_completed(futures):
            name = futures[fut]
            row = fut.result()
            row["job"] = name
            results.append(row)
            max_exit = max(max_exit, int(row["exit_code"]))

    if any(r["job"] == "profile_matrix" and r["exit_code"] == 0 for r in results):
        retry = _run("scripts/comp_atom05_compare_prior_v1.py")
        retry["job"] = "compare_after_matrix"
        results.append(retry)
        max_exit = max(max_exit, int(retry["exit_code"]))

    results.sort(key=lambda r: r.get("job", ""))
    doc = {
        "schema": "comp_atom05_parallel_bundle_v1",
        "generated_at_utc": _utc(),
        "tracks": results,
        "artifacts": {
            "profile_matrix": "reports/constitution/btrack_pilot/comp_atom05_profile_matrix_sweep_v1.json",
            "compare_prior": "reports/constitution/btrack_pilot/comp_atom05_compare_prior_v1.json",
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "tracks": results}, ensure_ascii=False))
    return max_exit


if __name__ == "__main__":
    raise SystemExit(main())
