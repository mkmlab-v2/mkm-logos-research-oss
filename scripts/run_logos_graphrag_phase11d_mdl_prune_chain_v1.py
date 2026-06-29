#!/usr/bin/env python3
"""Phase 11-D chain: MDL prune PoC + GATE_SPEC baseline refresh + gate eval [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11d_mdl_prune_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, optional: bool = False) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    ok = proc.returncode == 0
    row = {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": ok,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }
    if not ok and not optional:
        raise SystemExit(f"{label} failed rc={proc.returncode}\n{row['tail']}")
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-mdl", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    if not args.skip_mdl:
        steps.append(_run("mdl_prune_poc", [PY, "scripts/run_universal_root_mdl_prune_poc_v1.py"]))
        steps.append(_run("mdl_prune_gate", [PY, "scripts/check_universal_root_mdl_prune_gate_v1.py"]))
    steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
    steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))
    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_mdl_poc",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_universal_root_mdl_prune_poc_v1.py",
                    "-q",
                    "--tb=short",
                ],
                optional=True,
            )
        )

    poc = ROOT / "reports/universal_root_mdl_prune_poc_v1_latest.json"
    poc_doc = json.loads(poc.read_text(encoding="utf-8-sig")) if poc.is_file() else {}
    gate = ROOT / "reports/universal_root_mdl_prune_gate_v1_latest.json"
    gate_doc = json.loads(gate.read_text(encoding="utf-8-sig")) if gate.is_file() else {}

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_graphrag_phase11d_mdl_prune_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "mdl_any_sweep_pass": poc_doc.get("any_sweep_pass"),
        "mdl_baseline_jaccard": poc_doc.get("baseline_jaccard"),
        "mdl_gate_ok": gate_doc.get("gate_ok"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11d_mdl_prune_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "mdl_any_sweep_pass": poc_doc.get("any_sweep_pass"),
                "mdl_gate_ok": gate_doc.get("gate_ok"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
