#!/usr/bin/env python3
"""권장 원클릭: gold bootstrap → eval_r4 → v4 pilot sweep → semantic_rag_bridge."""
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
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_V4 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"
DEFAULT_BRIDGE_OUT = ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json"
DEFAULT_ROUTINE_OUT = PILOT / "comp_logos_rag_recommended_routine_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "step": label,
        "exit_code": proc.returncode,
        "stderr_tail": (proc.stderr or proc.stdout or "")[-500:] if proc.returncode else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pilot-sweep", action="store_true")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_ROUTINE_OUT)
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    steps.append(
        _run(
            [py, str(ROOT / "scripts/bootstrap_logos_query_gold_human_v1.py"), "--fill-empty-with-top1"],
            "bootstrap_gold_top1",
        )
    )
    steps.append(_run([py, str(ROOT / "scripts/run_logos_rag_retrieval_eval_r4_v1.py")], "eval_r4"))
    steps.append(_run([py, str(ROOT / "scripts/run_logos_rag_pilot_r4_batch_v1.py")], "pilot_r4_batch"))

    pilot_paths: list[str] = []
    if not args.skip_pilot_sweep and DEFAULT_V4.is_file():
        v4 = json.loads(DEFAULT_V4.read_text(encoding="utf-8-sig"))
        for it in v4.get("items") or []:
            if not isinstance(it, dict):
                continue
            qid = str(it.get("id") or "q")
            ko = str(it.get("query_ko") or "").strip()
            if not ko:
                continue
            out = PILOT / f"philosophy_lane_rag_pilot_r4_{qid}_ko_latest.json"
            steps.append(
                _run(
                    [
                        py,
                        str(ROOT / "scripts/philosophy_lane_rag_pilot_v1.py"),
                        "--user-query",
                        ko,
                        "--top-k",
                        "5",
                        "--out",
                        str(out),
                    ],
                    f"pilot_{qid}",
                )
            )
            if out.is_file():
                pilot_paths.append(str(out))

    bridge_pilot = PILOT / "philosophy_lane_rag_pilot_r4_q01_ko_latest.json"
    if not bridge_pilot.is_file():
        bridge_pilot = PILOT / "philosophy_lane_rag_pilot_r4_ko_probe_latest.json"
    steps.append(
        _run(
            [
                py,
                str(ROOT / "scripts/build_semantic_rag_bridge_insight_bundle_v1.py"),
                "--philosophy-pilot-json",
                str(bridge_pilot),
                "--calibration-kind",
                "none",
                "--out",
                str(DEFAULT_BRIDGE_OUT),
            ],
            "semantic_rag_bridge",
        )
    )

    eval_path = PILOT / "comp_logos_rag_retrieval_eval_r4_latest.json"
    eval_summary: dict[str, Any] = {}
    if eval_path.is_file():
        eval_summary = json.loads(eval_path.read_text(encoding="utf-8")).get("summary") or {}

    doc = {
        "schema": "comp_logos_rag_recommended_routine_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "steps": steps,
        "eval_r4_summary": eval_summary,
        "bridge_pilot_json": str(bridge_pilot),
        "pilot_sweep_count": len(pilot_paths),
        "track_wall": {"prophecy_promotion_gates_touch": False},
    }
    failed = [s for s in steps if s.get("exit_code") != 0]
    doc["ok"] = not failed
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(args.output_json), "failed_steps": len(failed)}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
