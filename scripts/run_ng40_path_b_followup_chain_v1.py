#!/usr/bin/env python3
"""[HYPO] Path B follow-up: prior+41k, tri-lane hybrid, pareto, research sign-off packet.

Does NOT run --apply-active. Commander LUT/signoff already done; this sets research export_prep.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_MANIFEST = ROOT / "reports/ng40_path_b_followup_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:500]}
    return {
        "script": script,
        "args": extra or [],
        "exit_code": int(cp.returncode),
        "parsed": parsed,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--human-approve-research",
        action="store_true",
        default=True,
        help="Refresh promotion packet with research sign-off (default on)",
    )
    ap.add_argument("--skip-pareto", action="store_true")
    ap.add_argument("--skip-auto-ops", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("scripts/run_ng40_path_b_prior_41k_eval_v1.py"))
    if steps[-1]["exit_code"] != 0:
        return steps[-1]["exit_code"]

    steps.append(_run("scripts/run_nextgen_hybrid_spine_trilane_stack_v1.py"))
    steps.append(_run("scripts/run_nextgen_science_prior_sidecar_chain_v1.py"))
    if not args.skip_pareto:
        steps.append(_run("scripts/run_nextgen_commercialization_pareto_sweep_v1.py"))

    pkt_extra: list[str] = []
    if args.human_approve_research:
        pkt_extra.extend(
            [
                "--human-approve-research",
                "--reviewer",
                "commander",
                "--note",
                "Path B knee + prior_41k research sign-off 2026-06-21",
            ]
        )
    steps.append(_run("scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py", pkt_extra))

    if not args.skip_auto_ops:
        steps.append(_run("scripts/run_ng40_recommended_auto_ops_v1.py"))

    packet = {}
    pkt_path = ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json"
    if pkt_path.is_file():
        packet = json.loads(pkt_path.read_text(encoding="utf-8-sig"))

    prior_path = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_prior_41k_v1_latest.json"
    )
    prior_doc = json.loads(prior_path.read_text(encoding="utf-8-sig")) if prior_path.is_file() else {}

    manifest = {
        "schema": "ng40_path_b_followup_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "prior_41k": {
            "beat_frozen": (prior_doc.get("beat_check") or {}).get("beat_frozen"),
            "saving": (prior_doc.get("aggregate") or {}).get("global_token_saving_rate"),
            "jaccard": (prior_doc.get("aggregate") or {}).get(
                "avg_reconstruction_fidelity_jaccard"
            ),
            "path": str(prior_path.relative_to(ROOT)).replace("\\", "/")
            if prior_path.is_file()
            else None,
        },
        "promotion_packet": {
            "export_prep_ready": packet.get("export_prep_ready"),
            "research_signoff_ready": packet.get("research_signoff_ready"),
            "commander_research_approval": packet.get("commander_research_approval"),
            "selected_arm": packet.get("selected_arm"),
            "apply_forbidden": packet.get("apply_forbidden"),
        },
        "knee_summary": "reports/ng40_path_b_knee_summary_v1_latest.json",
        "steps": steps,
        "forbidden": ["--apply-active without strict_beat active_best"],
    }
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"wrote": str(OUT_MANIFEST), **manifest["promotion_packet"]}, ensure_ascii=False))
    hard = any(s.get("exit_code") not in (0, None) for s in steps[:2])
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
