#!/usr/bin/env python3
"""COMP-ATOM-05 parallel: OpenAPI contract pytest + atom05 bundle + compare refresh."""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_atom05_parallel_docs_ci_v1.json"


def _utc() -> str:
    from datetime import timezone as tz

    return datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        "stdout_tail": (proc.stdout or "").strip()[-500:],
        "stderr_tail": (proc.stderr or "").strip()[-300:],
    }


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
        "stdout_tail": (proc.stdout or "").strip()[-400:],
        "stderr_tail": (proc.stderr or "").strip()[-200:],
    }


def _job_v2_contract() -> dict:
    return _pytest(
        [
            "tests/test_compression_token_api_v2_stub.py::test_openapi_v2_contract_has_graph_wire_selective_bridge",
            "tests/test_v2_graph_wire_selective_bridge_v1.py",
        ]
    )


def _job_atom05_bundle() -> dict:
    return _pytest(
        [
            "tests/test_mkm_graph_wire_bridge_influence_v1.py",
            "tests/test_comp_atom05_graph_wire_bridge_smoke_v1.py",
            "tests/test_multilens_performance_eval_report.py::test_evaluate_report_emit_semantic_pointer_smoke",
        ]
    )


def _job_compare() -> dict:
    return _run_py("scripts/comp_atom05_compare_prior_v1.py")


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("v2_openapi_contract", _job_v2_contract),
        ("atom05_pytest_bundle", _job_atom05_bundle),
        ("compare_prior", _job_compare),
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

    results.sort(key=lambda r: r.get("job", ""))
    doc = {
        "schema": "comp_atom05_parallel_docs_ci_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "tracks": results,
        "openapi": "docs/final/openapi_token_compression_v2_draft.yaml",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "tracks": results}, ensure_ascii=False))
    return max_exit


if __name__ == "__main__":
    raise SystemExit(main())
