#!/usr/bin/env python3
"""Phase 11-H: refresh Logos GraphRAG bridge evidence pack after Phase 11 layer stack."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
EVIDENCE_JSON = ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json"
GATE_SPEC = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json"
CHAIN_OUT = ROOT / "reports/logos_graphrag_phase11h_evidence_pack_chain_v1_latest.json"


def _utc_now() -> str:
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
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=CHAIN_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    steps.append(_run("build_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_evidence_pack",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_logos_graphrag_bridge_evidence_pack_v1.py::test_build_logos_graphrag_bridge_evidence_pack_v1",
                    "-q",
                    "--tb=short",
                ],
            )
        )

    evidence_doc = json.loads(EVIDENCE_JSON.read_text(encoding="utf-8-sig")) if EVIDENCE_JSON.is_file() else {}
    phase11 = (
        (evidence_doc.get("phase_coverage") or {}).get("phase_11_universal_root_layer_stack") or {}
    )
    gate_spec_doc = json.loads(GATE_SPEC.read_text(encoding="utf-8-sig")) if GATE_SPEC.is_file() else {}
    baseline = gate_spec_doc.get("baseline_observed") if isinstance(gate_spec_doc.get("baseline_observed"), dict) else {}

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_graphrag_phase11h_evidence_pack_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "evidence_pack_path": str(EVIDENCE_JSON.relative_to(ROOT)).replace("\\", "/"),
        "gate_spec_phase": baseline.get("phase"),
        "phase11_shallow_stress_hit_rate": (
            (phase11.get("shallow_stress_live_32") or {}).get("router_hit_rate")
        ),
        "phase11_shallow_stress_gap": (
            (phase11.get("shallow_stress_live_32") or {}).get("routing_oracle_gap")
        ),
        "phase11_sidecar_ablation_v2_ok": (
            (phase11.get("layer_b_subgraph_sidecar_ablation_v2") or {}).get("all_ok")
        ),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11h_evidence_pack_chain_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "gate_spec_phase": baseline.get("phase"),
                "shallow_hit_rate": report["phase11_shallow_stress_hit_rate"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
