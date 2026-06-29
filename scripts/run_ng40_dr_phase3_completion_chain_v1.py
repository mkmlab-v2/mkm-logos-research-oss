#!/usr/bin/env python3
"""[HYPO] DR Phase 3+4 completion — routing confidence manifest + latent knee acceptance.

research_only · send_gate HOLD · never --apply-active.
"""
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
OUT = ROOT / "reports/ng40_dr_phase3_completion_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(step_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": int(proc.returncode),
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-routing-manifest", action="store_true")
    ap.add_argument("--skip-knee-summary", action="store_true")
    ap.add_argument("--skip-path-b-followup", action="store_true")
    ap.add_argument("--skip-codec-split", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_routing_manifest:
        steps.append(
            _run(
                "routing_confidence_manifest",
                [PY, "scripts/build_compression_routing_confidence_ng40_manifest_v1.py"],
            )
        )

    if not args.skip_knee_summary:
        steps.append(_run("path_b_knee_summary", [PY, "scripts/build_ng40_path_b_knee_summary_v1.py"]))

    if not args.skip_codec_split:
        steps.append(
            _run(
                "codec_bench_split_refresh",
                [PY, "scripts/run_ng40_codec_bench_split_chain_v1.py", "--skip-path-b-sweep"],
            )
        )

    if not args.skip_path_b_followup:
        steps.append(
            _run(
                "path_b_followup",
                [
                    PY,
                    "scripts/run_ng40_path_b_followup_chain_v1.py",
                    "--skip-pareto",
                    "--skip-auto-ops",
                ],
            )
        )

    failed = [s for s in steps if s["exit_code"] != 0]
    routing = _load("reports/compression_routing_confidence_ng40_manifest_v1_latest.json")
    knee = _load("reports/ng40_path_b_knee_summary_v1_latest.json")
    followup = _load("reports/ng40_path_b_followup_chain_v1_latest.json")

    doc: dict[str, Any] = {
        "schema": "ng40_dr_phase3_completion_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "chain_ok": len(failed) == 0,
        "failed_steps": [s["id"] for s in failed],
        "steps": steps,
        "phase3_routing": {
            "case_count": len((routing or {}).get("per_case") or []),
            "shard_count": len((routing or {}).get("per_shard") or {}),
            "lowest_confidence": (routing or {})
            .get("routing_insights", {})
            .get("lowest_confidence_cases", [])[:3],
        },
        "phase4_latent_acceptance": {
            "dual_beat_possible": (knee or {}).get("dual_beat_any"),
            "knee_saving_max": (knee or {}).get("saving_max_knee", {}).get("global_token_saving_rate"),
            "conclusion_ko": (
                "latent ng40 cap grid = Pareto ceiling — dual beat 없음 수용. "
                "상용 헤드라인은 Path A B2B spine 22.29%."
            ),
        },
        "path_b_followup": {
            "export_prep_ready": (followup or {}).get("promotion_packet", {}).get("export_prep_ready"),
            "prior_41k_beat_frozen": (followup or {}).get("prior_41k", {}).get("beat_frozen"),
            "apply_forbidden": (followup or {}).get("promotion_packet", {}).get("apply_forbidden"),
        },
        "pointers": {
            "routing_manifest": "reports/compression_routing_confidence_ng40_manifest_v1_latest.json",
            "knee_summary": "reports/ng40_path_b_knee_summary_v1_latest.json",
            "path_b_followup": "reports/ng40_path_b_followup_chain_v1_latest.json",
            "phase2_chain": "reports/ng40_dr_phase2_completion_chain_v1_latest.json",
        },
        "reproducible_command": "py scripts/run_ng40_dr_phase3_completion_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": doc["chain_ok"], "failed_steps": doc["failed_steps"]}, ensure_ascii=False))
    return 0 if doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
