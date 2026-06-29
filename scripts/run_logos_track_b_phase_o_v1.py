#!/usr/bin/env python3
"""Phase O — Psi logic transplant + simplicial ledger + B2B chain + path gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
REPORTS = ROOT / "reports"
OUT_DEFAULT = REPORTS / "logos_track_b_phase_o_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-registry", action="store_true")
    ap.add_argument("--skip-closure", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("psi_logic_extraction", [PY, "scripts/build_logos_psi_logic_extraction_v1.py"]))
    steps.append(_run("simplicial_ledger", [PY, "scripts/build_logos_causal_simplicial_ledger_v1.py"]))
    steps.append(_run("b2b_deterministic_chain", [PY, "scripts/run_logos_b2b_deterministic_chain_v1.py"]))
    steps.append(_run("path_verification_gate", [PY, "scripts/build_logos_path_verification_gate_v1.py"]))
    steps.append(_run("lexicon_4d_research_audit", [PY, "scripts/run_logos_lexicon_4d_research_audit_v1.py", "--skip-phase-pa"]))
    steps.append(_run("b2b_mapping_audit", [PY, "scripts/build_logos_b2b_logic_mapping_audit_v1.py"]))
    steps.append(_run("phase_o_digest", [PY, "scripts/build_logos_phase_o_digest_v1.py"]))
    steps.append(_run("research_product_metrics", [PY, "scripts/build_logos_research_product_metrics_v1.py"]))
    steps.append(_run("completion_gate", [PY, "scripts/build_logos_phase_o_completion_gate_v1.py"]))

    if not args.skip_registry:
        steps.append(_run("reasoning_registry", [PY, "scripts/build_logos_reasoning_pattern_registry_v1.py"]))
    if not args.skip_closure:
        steps.append(_run("integration_closure", [PY, "scripts/build_logos_track_b_integration_closure_v1.py"]))

    ledger_path = REPORTS / "logos_track_b_research_v1_latest.json"
    chain_path = REPORTS / "logos_b2b_deterministic_chain_v1_latest.json"
    path_gate_path = REPORTS / "logos_path_verification_gate_v1_latest.json"
    simplicial_path = REPORTS / "logos_causal_simplicial_snapshot_v1_latest.json"

    ledger = json.loads(ledger_path.read_text(encoding="utf-8-sig")) if ledger_path.is_file() else {}
    chain = json.loads(chain_path.read_text(encoding="utf-8-sig")) if chain_path.is_file() else {}
    path_gate = json.loads(path_gate_path.read_text(encoding="utf-8-sig")) if path_gate_path.is_file() else {}
    simplicial = json.loads(simplicial_path.read_text(encoding="utf-8-sig")) if simplicial_path.is_file() else {}

    record_count = int(ledger.get("record_count") or len(ledger.get("records") or []))
    hub_triangles = int(simplicial.get("hub_triangles_seeded") or 0)
    chain_ok = (chain.get("summary") or {}).get("chain_complete") is True
    path_ok = (path_gate.get("summary") or {}).get("gate_pass") is True or float(
        (path_gate.get("summary") or {}).get("pass_rate") or 0
    ) >= 0.5
    completion_path = REPORTS / "logos_phase_o_completion_gate_v1_latest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8-sig")) if completion_path.is_file() else {}
    completion_score = float(completion.get("completion_score") or 0)
    completion_pass = completion.get("completion_pass") is True
    overall_ok = (
        all(s.get("ok") for s in steps)
        and record_count >= 2
        and chain_ok
        and completion_pass
    )

    doc = {
        "schema": "logos_track_b_phase_o_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "content_layer_isolated": True,
        "structure_transplant_only": True,
        "ledger_records": record_count,
        "hub_triangles_seeded": hub_triangles,
        "b2b_chain_coherence_ok": (chain.get("summary") or {}).get("coherence_ok"),
        "path_verification_pass_rate": (path_gate.get("summary") or {}).get("pass_rate"),
        "path_verification_gate_pass": path_ok,
        "completion_score": completion_score,
        "completion_pass": completion_pass,
        "artifacts": {
            "digest_md": "reports/logos_phase_o_digest_v1_latest.md",
            "research_ledger": "reports/logos_track_b_research_v1_latest.json",
            "psi_extraction": "reports/logos_psi_logic_extraction_v1_latest.json",
            "simplicial_snapshot": "reports/logos_causal_simplicial_snapshot_v1_latest.json",
            "b2b_chain": "reports/logos_b2b_deterministic_chain_v1_latest.json",
            "path_gate": "reports/logos_path_verification_gate_v1_latest.json",
            "completion_gate": "reports/logos_phase_o_completion_gate_v1_latest.json",
            "mapping_audit": "reports/logos_b2b_logic_mapping_audit_v1_latest.json",
        },
        "steps": steps,
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_track_b_phase_o_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": overall_ok,
                "ledger_records": record_count,
                "hub_triangles": hub_triangles,
                "path_gate_pass": path_ok,
                "completion_score": completion_score,
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
