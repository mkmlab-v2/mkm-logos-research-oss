#!/usr/bin/env python3
"""COMP-ATOM-05 parallel: subset JSON + pytest + wire sweep."""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_atom05_parallel_tracks_v1.json"


def _utc() -> str:
    from datetime import timezone as tz

    return datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_py(script_rel: str, extra: list[str] | None = None) -> dict:
    cmd = [sys.executable, str(ROOT / script_rel), *(extra or [])]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "track": script_rel,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").strip()[-600:],
        "stderr_tail": (proc.stderr or "").strip()[-300:],
    }


def _run_pytest(test_path: str) -> dict:
    cmd = [sys.executable, "-m", "pytest", test_path, "-q"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "track": test_path,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").strip()[-400:],
        "stderr_tail": (proc.stderr or "").strip()[-300:],
    }


def _job_build_subset() -> dict:
    return _run_py("scripts/build_multilens_logos_graph_subset_v1.py")


def _job_pytest_influence() -> dict:
    return _run_pytest("tests/test_mkm_graph_wire_bridge_influence_v1.py")


def _job_pytest_smoke() -> dict:
    return _run_pytest("tests/test_comp_atom05_graph_wire_bridge_smoke_v1.py")


def _job_atom05_sweep() -> dict:
    return _run_py("scripts/comp_atom05_graph_wire_bridge_sweep_v1.py")


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    jobs: list[tuple[str, object]] = [
        ("build_subset", _job_build_subset),
        ("pytest_influence", _job_pytest_influence),
        ("pytest_smoke", _job_pytest_smoke),
        ("atom05_sweep", _job_atom05_sweep),
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

    # subset must exist before sweep; re-run sweep if build finished after sweep failed
    if any(r["job"] == "build_subset" and r["exit_code"] == 0 for r in results):
        sweep = next((r for r in results if r["job"] == "atom05_sweep"), None)
        if sweep and sweep["exit_code"] != 0:
            retry = _run_py("scripts/comp_atom05_graph_wire_bridge_sweep_v1.py")
            retry["job"] = "atom05_sweep_retry"
            results.append(retry)
            max_exit = max(max_exit, int(retry["exit_code"]))

    results.sort(key=lambda r: r.get("job", ""))
    doc = {
        "schema": "comp_atom05_parallel_tracks_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "tracks": results,
        "artifacts": {
            "subset": "docs/final/artifacts/MULTILENS_LOGOS_GRAPH_SUBSET_V1.json",
            "sweep": "reports/constitution/btrack_pilot/comp_atom05_graph_wire_bridge_sweep_v1.json",
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "tracks": results}, ensure_ascii=False))
    return max_exit


if __name__ == "__main__":
    raise SystemExit(main())
