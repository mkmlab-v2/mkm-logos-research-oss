#!/usr/bin/env python3
"""Push parallel: thematic precision v7 → eval → experiments → L3 readiness → bridge."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports/constitution/btrack_pilot"
BRIDGE = ART / "semantic_rag_bridge_insight_bundle_v1_latest.json"
MERGED = PILOT / "philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_push_parallel_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "step": label,
        "exit_code": proc.returncode,
        "stderr_tail": None if proc.returncode == 0 else (proc.stderr or proc.stdout or "")[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    steps.append(_run([py, str(ROOT / "scripts/apply_logos_rag_thematic_precision_v7_v1.py")], "thematic_precision_v7"))
    steps.append(_run([py, str(ROOT / "scripts/run_logos_rag_dual_gold_eval_v1.py")], "dual_eval"))
    steps.append(_run([py, str(ROOT / "scripts/run_logos_rag_retrieval_eval_r4_v1.py")], "eval_r4"))
    steps.append(_run([py, str(ROOT / "scripts/run_logos_rag_btrack_search_experiments_v1.py")], "btrack_experiments"))
    steps.append(_run([py, str(ROOT / "scripts/build_logos_rag_l3_readiness_v1.py")], "l3_readiness"))
    steps.append(_run([py, str(ROOT / "scripts/check_logos_rag_btrack_promotion_gate_v1.py")], "gate"))
    steps.append(
        _run(
            [
                py,
                str(ROOT / "scripts/build_semantic_rag_bridge_insight_bundle_v1.py"),
                "--philosophy-pilot-json",
                str(MERGED),
                "--track",
                "Track_C_advisory",
                "--gating",
                "NON_GATING",
                "--calibration-kind",
                "none",
                "--out",
                str(BRIDGE),
            ],
            "bridge_refresh",
        )
    )

    dual = {}
    dpath = PILOT / "comp_logos_rag_dual_gold_eval_v1_latest.json"
    if dpath.is_file():
        dual = json.loads(dpath.read_text(encoding="utf-8-sig")).get("summary") or {}
    l3 = {}
    l3path = ART / "logos_rag_l3_readiness_v1_latest.json"
    if l3path.is_file():
        l3 = json.loads(l3path.read_text(encoding="utf-8-sig"))

    failed = [s for s in steps if s.get("exit_code", 0) != 0]
    doc = {
        "schema": "comp_logos_rag_push_parallel_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "ok": not failed,
        "steps": steps,
        "dual_eval_summary": dual,
        "l3_readiness": {
            "approval_ready": l3.get("approval_ready"),
            "action": l3.get("recommended_commander_action"),
            "st_mean": (l3.get("btrack_st_u_index") or {}).get("mean_top1_ko"),
        },
        "track_wall": {"l3_prod_swap": False, "l3_recorded": False},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": not failed, "dual": dual, "l3": doc["l3_readiness"]}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
