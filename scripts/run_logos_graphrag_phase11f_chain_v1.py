#!/usr/bin/env python3
"""Phase 11-F: shallow NSM wire + sidecar ablation v2 + GATE_SPEC refresh [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11f_chain_v1_latest.json"


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


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-nsm-wire", action="store_true")
    ap.add_argument("--skip-ablation", action="store_true")
    ap.add_argument("--ablation-quick", action="store_true", help="Pairwise subset for faster runs")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    if not args.skip_nsm_wire:
        steps.append(_run("p3_root_nsm_wire", [PY, "scripts/run_p3_root_nsm_wire_chain_v1.py"]))
    if not args.skip_ablation:
        ablation_cmd = [PY, "scripts/run_logos_subgraph_sidecar_ablation_v2_v1.py"]
        if args.ablation_quick:
            ablation_cmd.append("--quick")
        steps.append(_run("sidecar_ablation_v2", ablation_cmd))
    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))
    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_ablation_v2_quick",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_run_logos_subgraph_sidecar_ablation_v2_v1.py",
                    "-q",
                    "--tb=short",
                ],
                optional=True,
            )
        )

    nsm_doc = _read_json(ROOT / "reports/p3_root_nsm_wire_chain_v1_latest.json")
    ablation_doc = _read_json(ROOT / "reports/logos_subgraph_sidecar_ablation_v2_latest.json")
    gate_doc = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_graphrag_phase11f_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "nsm_wire_ok": nsm_doc.get("ok"),
        "oracle_gap": (nsm_doc.get("oracle_gap_summary") or {}).get("routing_oracle_gap"),
        "sidecar_ablation_v2_ok": ablation_doc.get("all_ok"),
        "sidecar_ablation_no_regression": ablation_doc.get("no_hit_at_1_regression"),
        "sidecar_config_count": ablation_doc.get("config_count"),
        "gate_schema_ok": gate_doc.get("schema_validation_ok"),
        "all_enabled_planes_ok": (gate_doc.get("evaluation") or {}).get("all_enabled_planes_ok"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11f_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "nsm_wire_ok": report["nsm_wire_ok"],
                "ablation_configs": report["sidecar_config_count"],
                "no_regression": report["sidecar_ablation_no_regression"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
