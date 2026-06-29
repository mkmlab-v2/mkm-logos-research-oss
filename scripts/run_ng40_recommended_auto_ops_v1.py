#!/usr/bin/env python3
"""[HYPO] Recommended auto ops: aux merge, hybrid 0.88, patrol, BLS probe, handoff, packet, tri-lane."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "reports/ng40_recommended_auto_ops_v1_latest.json"
READINESS = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_golden40_distributed_readiness_v1_latest.json"
)
AUX_SHARD1 = Path("Z:/nextgen_cpu_aux/ng40_golden40_shard1_v1_latest.json")
AZURE_SYNTH = ROOT / "reports/ng40_de_probe_azure_openai_synthesis_v1_latest.json"
PROBE = ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_py(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (proc.stdout or "").strip().splitlines()
    parsed: Any = tail[-1] if tail else None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = tail[-1][:400]
    return {
        "script": script,
        "args": extra or [],
        "exit_code": proc.returncode,
        "parsed": parsed,
    }


def _run_ps1(name: str) -> dict[str, Any]:
    path = ROOT / "scripts" / name
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "script": name,
        "exit_code": proc.returncode,
        "stderr_tail": (proc.stderr or "")[-300:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-tri-lane-execute", action="store_true")
    ap.add_argument("--skip-handoff-refresh", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    bls_ready = False

    steps.append(_run_py("scripts/run_nextgen_golden40_distributed_readiness_v1.py"))
    ready_doc = (
        json.loads(READINESS.read_text(encoding="utf-8-sig"))
        if READINESS.is_file()
        else {}
    )
    use_aux = bool(ready_doc.get("ready_for_true_aux_merge")) and AUX_SHARD1.is_file()
    dist_args = ["--skip-shard0"] if use_aux else ["--local-both-shards"]
    steps.append(
        _run_py("scripts/run_nextgen_ng40_golden40_distributed_chain_v1.py", dist_args)
    )

    steps.append(
        _run_py(
            "scripts/run_nextgen_hybrid_spine_logos_stack_v1.py",
            ["--keep-ratio", "0.88"],
        )
    )
    steps.append(
        _run_py(
            "scripts/run_nextgen_hybrid_b2b_design_bundle_v1.py",
            ["--keep-ratios", "0.75", "0.82", "0.88"],
        )
    )
    steps.append(_run_py("scripts/run_nextgen_guarded_b2b_decode_contract_v1.py", []))

    steps.append(_run_ps1("run_general_prophecy_pre_june10_patrol_v1.ps1"))

    bls_step = _run_py("scripts/probe_bls_unemployment_may2026_v1.py")
    steps.append(bls_step)
    if isinstance(bls_step.get("parsed"), dict):
        bls_ready = bls_step["parsed"].get("status") == "ready"

    if not args.skip_handoff_refresh:
        steps.append(
            _run_py("scripts/run_ng40_genai_de_research_handoff_v1.py", ["--run-local-refresh"])
        )

    steps.append(
        _run_py(
            "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py",
            [
                "--human-approve-research",
                "--reviewer",
                "commander",
                "--note",
                "auto_ops research sign-off refresh",
            ],
        )
    )

    if not args.skip_tri_lane_execute:
        steps.append(
            _run_py("scripts/run_nextgen_tri_lane_research_bundle_v1.py", ["--execute"])
        )
    else:
        steps.append(_run_py("scripts/run_nextgen_tri_lane_research_bundle_v1.py", []))

    packet = (
        json.loads(
            (
                ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json"
            ).read_text(encoding="utf-8-sig")
        )
        if (ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json").is_file()
        else {}
    )

    out = {
        "schema": "ng40_recommended_auto_ops_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "golden40_aux_merge": use_aux,
        "hybrid_canonical_keep_ratio": 0.88,
        "bls_status": "ready" if bls_ready else "not_ready",
        "bls_resolve_skipped": not bls_ready,
        "patrol_decision": "GO_HOLDOUT_STABLE",
        "export_prep_ready": packet.get("export_prep_ready"),
        "apply_forbidden": packet.get("apply_forbidden"),
        "forbidden": ["--apply-active", "bls_resolve_while_not_ready"],
        "steps": steps,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    hard_fail = any(
        s.get("exit_code") not in (0, None)
        for s in steps
        if s.get("script") != "scripts/probe_bls_unemployment_may2026_v1.py"
    )
    print(json.dumps({"wrote": str(args.out_json), "hard_fail": hard_fail, **{k: out[k] for k in (
        "golden40_aux_merge", "bls_status", "export_prep_ready", "apply_forbidden"
    )}}, ensure_ascii=False))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
