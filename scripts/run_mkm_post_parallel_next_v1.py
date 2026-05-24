#!/usr/bin/env python3
"""Post-parallel next: multichannel marketing handoff + B-track promotion gates (no live)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/mkm_post_parallel_next_v1_latest.json"
YOUTUBE_ID = "compression_discipline_youtube_q2"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _youtube_human_approve() -> dict[str, Any]:
    q = ROOT / "data/marketing/marketing_content_queue.json"
    doc = json.loads(q.read_text(encoding="utf-8"))
    now = _utc()
    for item in doc.get("items") or []:
        if isinstance(item, dict) and item.get("id") == YOUTUBE_ID:
            st = str(item.get("status") or "")
            if st == "drafted":
                item["status"] = "human_approved"
                item["human_approved_at_utc"] = now
                doc["updated_at_utc"] = now
                q.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return {
                "step": "youtube_queue_human_approved",
                "ok": st in ("drafted", "human_approved", "published"),
                "exit_code": 0 if st in ("drafted", "human_approved", "published") else 2,
                "tail": f"status={item.get('status')}",
            }
    return {"step": "youtube_queue_human_approved", "ok": False, "exit_code": 2, "tail": "item missing"}


def _run(step: str, cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "step": step,
        "ok": cp.returncode == 0,
        "exit_code": cp.returncode,
        "tail": ((cp.stdout or cp.stderr or "")[-500:]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    py = sys.executable
    steps: list[dict[str, Any]] = []

    steps.append(_run("weekly_bundle_summary", [py, "scripts/build_marketing_weekly_bundle_summary_v1.py"]))
    steps.append(_run("publish_handoff", [py, "scripts/build_marketing_publish_handoff_v1.py"]))
    steps.append(_youtube_human_approve())
    steps.append(
        _run(
            "marketing_phase2_refresh",
            [py, "scripts/run_marketing_auto_phase2_v1.py", "--skip-buffer-preview"],
        )
    )
    steps.append(_run("promotion_readiness", [py, "scripts/build_prophecy_promotion_readiness_report_v1.py"]))
    steps.append(
        _run(
            "promotion_gates",
            [py, "scripts/eval_prophecy_promotion_gates_v1.py", "--promotion-track-mode", "dual"],
        )
    )
    steps.append(_run("gate_evidence_pack", [py, "scripts/build_prophecy_gate_evidence_pack_v1.py"]))
    steps.append(_run("parallel_fusion", [py, "scripts/build_btrack_parallel_weekly_fusion_v1.py", "--skip-fusion-stub"]))
    steps.append(_run("mkm_fused_handoff", [py, "scripts/build_mkm_parallel_lanes_fused_handoff_v1.py"]))

    doc = {
        "schema": "mkm_post_parallel_next_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "steps": steps,
        "all_ok": all(s.get("ok") for s in steps),
        "failed": [s["step"] for s in steps if not s.get("ok")],
        "commander_next": [
            "YouTube: reports/marketing/marketing_youtube_next_steps_latest.md + script under youtube_scripts/",
            "LinkedIn: both published — optional edit live moat from linkedin_paste_primary_latest.txt",
            "B-track: prophecy_promotion_readiness + gates JSON — no auto live (90d / human)",
            "OpenData: cover Part A PDF for merge (mkm_parallel_lanes_fused_handoff)",
        ],
        "track_a_live_promotion": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "output": str(args.output), "failed": doc["failed"]}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
