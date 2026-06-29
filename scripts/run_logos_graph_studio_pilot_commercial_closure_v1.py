#!/usr/bin/env python3
"""Track C Logos Graph Studio pilot commercial closure chain (B-track · HOLD send)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graph_studio_pilot_commercial_closure_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_step(name: str, cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if len(tail) > 1500:
        tail = tail[-1500:]
    return {"step": name, "exit_code": proc.returncode, "ok": proc.returncode == 0, "tail": tail}


def _run_ps(script_rel: str, *extra: str) -> dict[str, Any]:
    script = ROOT / script_rel.replace("/", "\\")
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *extra,
    ]
    return _run_step(script_rel, cmd, timeout=900)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-vps", action="store_true", help="Skip sync_showroom_to_vps.ps1")
    ap.add_argument("--skip-ollama", action="store_true", help="Joint eval with --optional-ollama")
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    steps.append(
        _run_step(
            "lemma_verse_registry_heuristic",
            [
                PY,
                "scripts/build_logos_lemma_verse_edges_v1.py",
                "--registry-json",
                str(REGISTRY),
                "--graph-max-edges",
                "5000",
                "--graph-tokens-per-verse",
                "3",
            ],
        )
    )

    showroom_builds = [
        ("cosmic_meta_ui", [PY, "scripts/build_logos_cosmic_meta_architecture_ui_v1.py"]),
        ("era_insight_lattice", [PY, "scripts/build_showroom_era_insight_lattice_v1.py"]),
        ("meaning_topology_graph_slice", [
            PY,
            "scripts/build_showroom_meaning_topology_graph_slice_v1.py",
            "--seed-count",
            "14",
            "--max-nodes",
            "72",
            "--max-edges",
            "140",
        ]),
        ("qa_presets", [PY, "scripts/build_showroom_meaning_topology_qa_presets_v1.py"]),
        ("graph_wire_poc", [PY, "scripts/build_mkm_graph_wire_rag_poc_v1.py"]),
        ("dynamic_map_publish", [PY, "scripts/publish_logos_chronology_dynamic_map_showroom_v1.py"]),
    ]
    for name, cmd in showroom_builds:
        steps.append(_run_step(name, cmd))

    steps.append(_run_step("subgraph_gold_eval_chain", [PY, "scripts/run_logos_subgraph_gold_eval_chain_v1.py"]))

    joint_cmd = [
        PY,
        "scripts/run_logos_graphrag_ollama_joint_eval_v1.py",
        "--min-lemma-lines",
        "500",
        "--min-sinew-lines",
        "1000",
        "--min-osi-lines",
        "1000",
        "--min-theographic-lines",
        "1000",
    ]
    if args.skip_ollama:
        joint_cmd.append("--optional-ollama")
    steps.append(_run_step("joint_eval_pilot_tier", joint_cmd, timeout=300))

    steps.append(_run_step("track_l_l4_l5", [
        PY,
        "scripts/run_logos_track_l_l4_l5_readiness_v1.py",
        "--skip-l3",
    ]))
    steps.append(_run_step("evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))
    steps.append(_run_step("marketing_ip_gate", [PY, "scripts/check_mkm_marketing_ip_governance_v1.py"]))
    steps.append(_run_step("positioning_gate", [PY, "scripts/check_logos_showroom_positioning_fact_lock_v1.py"]))
    steps.append(
        _run_step("b2b_meeting_pack", [PY, "scripts/build_logos_graph_studio_b2b_meeting_pack_v1.py"])
    )
    steps.append(
        _run_step(
            "b2b_meeting_pack_readiness",
            [PY, "scripts/check_logos_graph_studio_b2b_meeting_pack_readiness_v1.py"],
        )
    )

    steps.append(_run_ps("projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1"))

    if not args.skip_vps:
        steps.append(
            _run_ps(
                "projects/bitcoin-trading/ops/windows-rehearsal/sync_showroom_to_vps.ps1",
                "-SkipDotenvUserSync",
            )
        )

    steps.append(_run_step("commercial_readiness", [PY, "scripts/build_logos_observatory_commercial_readiness_v1.py"]))

    # Rebuild pilot lemma after any downstream step that may touch lemma artifacts.
    steps.append(
        _run_step(
            "lemma_verse_pilot_finalize",
            [
                PY,
                "scripts/build_logos_lemma_verse_edges_v1.py",
                "--registry-json",
                str(REGISTRY),
                "--graph-max-edges",
                "5000",
                "--graph-tokens-per-verse",
                "3",
            ],
        )
    )

    steps.append(_run_step("pilot_commercial_gate", [PY, "scripts/check_logos_graph_studio_pilot_commercial_gate_v1.py"]))

    if not args.skip_pytest:
        steps.append(
            _run_step(
                "pytest_pilot_bundle",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_mkm_marketing_ip_governance_v1.py",
                    "tests/test_logos_showroom_positioning_fact_lock_v1.py",
                    "tests/test_build_mkm_graph_wire_rag_poc_v1.py",
                    "-q",
                    "--tb=short",
                ],
                timeout=180,
            )
        )

    failed = [s for s in steps if not s.get("ok")]
    doc = {
        "schema": "logos_graph_studio_pilot_commercial_closure_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "pilot_tier": True,
        "ok": len(failed) == 0,
        "failed_steps": [s["step"] for s in failed],
        "steps": steps,
        "reproducible_command": (
            "py scripts/run_logos_graph_studio_pilot_commercial_closure_v1.py --skip-vps"
        ),
        "boundary_ack": (
            "Pilot commercial stack closure — not full 31k GraphRAG SaaS, not counsel SEND, not Track A."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "failed": doc["failed_steps"], "out": str(args.output)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
