#!/usr/bin/env python3
"""One-shot: signoff restore → v4 weak auto thematic → dual eval → R6 bridge → gate."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = PILOT / "comp_logos_rag_auto_provisional_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "step": label,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-500:] if proc.stdout else None,
        "stderr_tail": (proc.stderr or "")[-500:] if proc.returncode and proc.stderr else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-signoff", action="store_true")
    ap.add_argument("--skip-bridge", action="store_true")
    ap.add_argument("--skip-pilots", action="store_true", help="Skip 12x ko_only pilot batch (slow).")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    gold_path = ART / "logos_semantic_query_gold_human_v1.json"
    needs_signoff = True
    if gold_path.is_file():
        g = json.loads(gold_path.read_text(encoding="utf-8-sig"))
        needs_signoff = str(g.get("signoff") or "") != "commander_approved" or not any(
            (it.get("gold_verse_ids_harness_top1") for it in (g.get("items") or []) if isinstance(it, dict))
        )

    if needs_signoff and not args.skip_signoff:
        steps.append(_run([py, str(ROOT / "scripts/apply_logos_rag_commander_gold_signoff_v1.py")], "signoff_restore"))

    steps.append(_run([py, str(ROOT / "scripts/apply_logos_rag_provisional_thematic_auto_v1.py")], "v4_weak_auto"))
    steps.append(_run([py, str(ROOT / "scripts/run_logos_rag_dual_gold_eval_v1.py")], "dual_eval"))

    if not args.skip_pilots:
        steps.append(
            _run(
                [py, str(ROOT / "scripts/run_logos_rag_r6_ko_only_lane_v1.py"), "--skip-signoff"],
                "r6_pilots",
            )
        )

    if not args.skip_bridge:
        steps.append(
            _run(
                [
                    py,
                    str(ROOT / "scripts/merge_logos_rag_pilot_ko_v1.py"),
                    "--glob",
                    "philosophy_lane_rag_pilot_r6_*_ko_only_latest.json",
                    "--out",
                    str(PILOT / "philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json"),
                    "--version-tag",
                    "1.2.0",
                ],
                "merge_r6",
            )
        )
        steps.append(
            _run(
                [
                    py,
                    str(ROOT / "scripts/build_semantic_rag_bridge_insight_bundle_v1.py"),
                    "--philosophy-pilot-json",
                    str(PILOT / "philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json"),
                    "--track",
                    "Track_C_advisory",
                    "--gating",
                    "NON_GATING",
                    "--calibration-kind",
                    "none",
                    "--route-confidence",
                    "0.7",
                    "--summary-line",
                    "P15 auto provisional v4_weak thematic + R6 ko_only bridge",
                ],
                "bridge",
            )
        )

    steps.append(
        _run([py, str(ROOT / "scripts/check_logos_rag_btrack_promotion_gate_v1.py"), "--run-pytest"], "gate")
    )
    steps.append(_run([py, str(ROOT / "scripts/build_logos_rag_promotion_review_packet_v1.py")], "review_packet"))

    dual_summary = {}
    dual_path = PILOT / "comp_logos_rag_dual_gold_eval_v1_latest.json"
    if dual_path.is_file():
        dual_summary = json.loads(dual_path.read_text(encoding="utf-8-sig")).get("summary") or {}

    gate = {}
    gate_path = ART / "logos_rag_btrack_promotion_gate_v1_latest.json"
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "comp_logos_rag_auto_provisional_chain_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "dual_eval_summary": dual_summary,
        "gate_action": gate.get("recommended_commander_action"),
        "gate_L2": (gate.get("tiers") or {}).get("L2_track_c_shadow_ingest", {}).get("passed"),
        "steps": steps,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    failed = [s["step"] for s in steps if s.get("exit_code") not in (0, None)]
    print(
        json.dumps(
            {
                "ok": not failed,
                "failed": failed,
                "dual_eval_summary": dual_summary,
                "gate_action": gate.get("recommended_commander_action"),
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
