#!/usr/bin/env python3
"""Smoke: ops_dynamical_bench_v1 schema + runner artifact."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/ops_dynamical_bench_v1.schema.json"
EXAMPLE = ROOT / "docs/final/schemas/ops_dynamical_bench_v1.example.json"
RUNNER = ROOT / "scripts/run_ops_dynamical_bench_v1.py"
OUT = ROOT / "reports/ops_dynamical_bench_smoke_v1_latest.json"


def main() -> int:
    doc: dict = {
        "schema": "ops_dynamical_bench_smoke_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "checks": {},
    }
    ok = True

    for label, path in [("schema", SCHEMA), ("example", EXAMPLE), ("runner", RUNNER)]:
        present = path.is_file()
        doc["checks"][f"{label}_exists"] = {"ok": present, "path": str(path).replace("\\", "/")}
        ok = ok and present

    try:
        import jsonschema  # type: ignore

        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        jsonschema.validate(instance=example, schema=schema)
        doc["checks"]["example_validates"] = {"ok": True}
    except Exception as exc:  # noqa: BLE001
        doc["checks"]["example_validates"] = {"ok": False, "error": str(exc)}
        ok = False

    proc = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    doc["checks"]["runner_exit_0"] = {"ok": proc.returncode == 0, "exit_code": proc.returncode}
    ok = ok and proc.returncode == 0

    jsonl_path = ROOT / "reports/ops_dynamical_timeseries_v1.jsonl"
    if jsonl_path.is_file():
        lines = [ln for ln in jsonl_path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
        doc["checks"]["jsonl_appended"] = {"ok": len(lines) >= 1, "rows": len(lines)}
        ok = ok and len(lines) >= 1
    else:
        doc["checks"]["jsonl_appended"] = {"ok": False, "rows": 0}
        ok = False

    l1_proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ops_dynamical_l1_eval_v1.py"), "--no-patch-bench-latest"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    doc["checks"]["l1_eval_exit_0"] = {"ok": l1_proc.returncode == 0, "exit_code": l1_proc.returncode}
    ok = ok and l1_proc.returncode == 0

    l2_proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ops_dynamical_l2_intervention_chain_v1.py"),
            "--mode",
            "synthetic",
            "--jsonl",
            str(ROOT / "reports/ops_dynamical_timeseries_l2_smoke_v1.jsonl"),
            "--out",
            str(ROOT / "reports/ops_dynamical_l2_intervention_chain_smoke_v1_latest.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    doc["checks"]["l2_synthetic_chain_exit_0"] = {"ok": l2_proc.returncode == 0, "exit_code": l2_proc.returncode}
    ok = ok and l2_proc.returncode == 0

    l3_proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ops_dynamical_l3_cross_fixture_eval_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    doc["checks"]["l3_cross_fixture_exit_0"] = {"ok": l3_proc.returncode == 0, "exit_code": l3_proc.returncode}
    ok = ok and l3_proc.returncode == 0

    l4_proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ops_dynamical_l4_clinical_eval_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    doc["checks"]["l4_clinical_eval_exit_0"] = {"ok": l4_proc.returncode == 0, "exit_code": l4_proc.returncode}
    ok = ok and l4_proc.returncode == 0

    bench_path = ROOT / "reports/ops_dynamical_bench_v1_latest.json"
    if bench_path.is_file() and ok:
        try:
            import jsonschema  # type: ignore

            schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
            bench = json.loads(bench_path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=bench, schema=schema)
            doc["checks"]["artifact_validates"] = {
                "ok": True,
                "stage": bench.get("state_machine", {}).get("stage"),
                "stress": bench.get("stress", {}).get("score"),
            }
        except Exception as exc:  # noqa: BLE001
            doc["checks"]["artifact_validates"] = {"ok": False, "error": str(exc)}
            ok = False
    else:
        doc["checks"]["artifact_validates"] = {"ok": False, "error": "missing_or_prior_fail"}
        ok = False

    doc["ok"] = ok
    doc["reproduce"] = "py scripts/check_ops_dynamical_bench_smoke_v1.py"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
