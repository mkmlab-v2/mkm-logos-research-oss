#!/usr/bin/env python3
"""Phase 16: GATE_SPEC topology crosswalk spec + offline 41k↔31k plane separation chain [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase16_topology_crosswalk_chain_v1_latest.json"
PHASE15 = ROOT / "reports/logos_graphrag_phase15_deepnsm_hf_checkpoint_chain_v1_latest.json"
TOPOLOGY_REPORT = ROOT / "reports/universal_root_topology_crosswalk_v1_latest.json"
TOPOLOGY_GATE = ROOT / "reports/universal_root_topology_crosswalk_gate_v1_latest.json"


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
    ap.add_argument("--skip-carry-verify", action="store_true")
    ap.add_argument("--skip-anchor-index", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument(
        "--sanitize-topology",
        action="store_true",
        help="Run GRASP stub defense bench (ID alignment + decoy) on public topology fixture",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_carry_verify:
        steps.append(
            _run(
                "gate_spec_enforce_carry",
                [PY, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"],
            )
        )
        phase15 = _read_json(PHASE15)
        steps.append(
            {
                "label": "phase15_carry_snapshot",
                "cmd": ["read_only"],
                "exit_code": 0,
                "ok": bool(phase15.get("all_ok")),
                "tail": json.dumps(
                    {
                        "phase15_all_ok": phase15.get("all_ok"),
                        "pair_count": phase15.get("pair_count"),
                        "prime_hit_rate": (phase15.get("hf_checkpoint_audit") or {}).get("prime_hit_rate"),
                    },
                    ensure_ascii=False,
                )[-500:],
            }
        )

    if not args.skip_anchor_index:
        steps.append(
            _run(
                "build_bidirectional_anchor_index",
                [PY, "scripts/build_logos_bidirectional_anchor_index_v1.py"],
                optional=True,
            )
        )

    steps.append(_run("build_topology_crosswalk", [PY, "scripts/build_universal_root_topology_crosswalk_v1.py"]))
    steps.append(_run("check_topology_crosswalk_gate", [PY, "scripts/check_universal_root_topology_crosswalk_v1.py"]))

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(
            _run(
                "check_gate_spec_enforce",
                [PY, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"],
            )
        )

    if not args.skip_evidence_pack:
        steps.append(_run("build_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_topology_crosswalk",
                [PY, "-m", "pytest", "tests/test_universal_root_topology_crosswalk_v1.py", "-q", "--tb=short"],
                optional=True,
            )
        )

    grasp_defense: dict = {}
    if args.sanitize_topology:
        grasp_step = _run(
            "topology_grasp_defense_bench",
            [PY, "scripts/decomposer/topology_security_filter_v1.py", "--decoy-ratio", "0.15", "--f1-gate", "0.15"],
        )
        steps.append(grasp_step)
        grasp_defense = _read_json(ROOT / "reports/topology_grasp_defense_bench_v1_latest.json")

    topo = _read_json(TOPOLOGY_REPORT)
    topo_gate = _read_json(TOPOLOGY_GATE)
    gate_eval = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_graphrag_phase16_topology_crosswalk_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "implementation_status": "topology_crosswalk_v1",
        "all_ok": all_ok,
        "ok": all_ok and bool(topo_gate.get("gate_ok")),
        "topology_gate_ok": bool(topo_gate.get("gate_ok")),
        "topology_summary": topo.get("summary") or {},
        "wall_divergence": topo.get("wall_divergence") or {},
        "lexicon_plane": topo.get("lexicon_plane") or {},
        "topology_plane": topo.get("topology_plane") or {},
        "delta_topology_minus_lexicon": topo.get("delta_topology_minus_lexicon") or {},
        "gate_schema_ok": gate_eval.get("schema_validation_ok"),
        "all_enabled_planes_ok": (gate_eval.get("evaluation") or {}).get("all_enabled_planes_ok"),
        "spec_pointer": "docs/final/artifacts/UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json",
        "steps": steps,
        "topology_grasp_defense": grasp_defense or None,
        "reproduce": "py scripts/run_logos_graphrag_phase16_topology_crosswalk_chain_v1.py",
        "reproduce_sanitize": "py scripts/run_logos_graphrag_phase16_topology_crosswalk_chain_v1.py --sanitize-topology",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "topology_gate_ok": report["topology_gate_ok"],
                "verse_reachable_rate": (topo.get("summary") or {}).get("verse_reachable_rate"),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
