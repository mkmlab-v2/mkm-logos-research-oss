#!/usr/bin/env python3
"""P15 R6: re-apply dual-track gold if needed, dual eval, 12x ko_only pilots, gate snapshot."""
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
DEFAULT_V4 = ART / "logos_semantic_query_set_v4_ko_en_v1.json"
DEFAULT_GOLD = ART / "logos_semantic_query_gold_human_v1.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_r6_ko_only_lane_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "step": label,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-400:] if proc.stdout else None,
        "stderr_tail": (proc.stderr or "")[-400:] if proc.returncode and proc.stderr else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-signoff", action="store_true")
    ap.add_argument("--skip-pilot-batch", action="store_true")
    ap.add_argument("--record-l2", action="store_true")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    gold_doc = json.loads(DEFAULT_GOLD.read_text(encoding="utf-8-sig")) if DEFAULT_GOLD.is_file() else {}
    needs_signoff = str(gold_doc.get("signoff") or "") != "commander_approved"
    if needs_signoff and not args.skip_signoff:
        steps.append(
            _run(
                [py, str(ROOT / "scripts/apply_logos_rag_commander_gold_signoff_v1.py")],
                "commander_gold_signoff",
            )
        )
    steps.append(_run([py, str(ROOT / "scripts/run_logos_rag_dual_gold_eval_v1.py")], "dual_gold_eval"))

    pilot_paths: list[str] = []
    if not args.skip_pilot_batch and DEFAULT_V4.is_file():
        v4 = json.loads(DEFAULT_V4.read_text(encoding="utf-8-sig"))
        for it in v4.get("items") or []:
            if not isinstance(it, dict):
                continue
            qid = str(it.get("id") or "q")
            en = str(it.get("query_en") or "").strip()
            ko = str(it.get("query_ko") or "").strip()
            if not en or not ko:
                continue
            out = PILOT / f"philosophy_lane_rag_pilot_r6_{qid}_ko_only_latest.json"
            steps.append(
                _run(
                    [
                        py,
                        str(ROOT / "scripts/philosophy_lane_rag_pilot_v1.py"),
                        "--query-en",
                        en,
                        "--query-ko",
                        ko,
                        "--rag-lane",
                        "ko_only",
                        "--top-k",
                        "5",
                        "--out",
                        str(out),
                    ],
                    f"pilot_ko_only_{qid}",
                )
            )
            if out.is_file():
                pilot_paths.append(str(out))

    gate_cmd = [py, str(ROOT / "scripts/check_logos_rag_btrack_promotion_gate_v1.py"), "--run-pytest"]
    steps.append(_run(gate_cmd, "promotion_gate"))
    gate = {}
    gate_path = ART / "logos_rag_btrack_promotion_gate_v1_latest.json"
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    l2_recorded = False
    if args.record_l2 and (gate.get("tiers") or {}).get("L2_track_c_shadow_ingest", {}).get("approval_ready"):
        rec = _run(
            [
                py,
                str(ROOT / "scripts/record_logos_rag_btrack_promotion_human_approval_v1.py"),
                "--tier",
                "L2",
                "--notes",
                "P15 R6: dual-track thematic gold + ko_only lane; harness not L2 quality claim.",
            ],
            "record_l2_approval",
        )
        steps.append(rec)
        l2_recorded = rec.get("exit_code") == 0

    dual_summary = {}
    dual_path = PILOT / "comp_logos_rag_dual_gold_eval_v1_latest.json"
    if dual_path.is_file():
        dual_summary = json.loads(dual_path.read_text(encoding="utf-8-sig")).get("summary") or {}

    doc = {
        "schema": "comp_logos_rag_r6_ko_only_lane_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "rag_lane": "ko_only",
        "pilot_outputs_n": len(pilot_paths),
        "pilot_paths": pilot_paths,
        "dual_eval_summary": dual_summary,
        "gate_L1": (gate.get("tiers") or {}).get("L1_btrack_lab_bundle", {}).get("passed"),
        "gate_L2": (gate.get("tiers") or {}).get("L2_track_c_shadow_ingest", {}).get("passed"),
        "recommended_action": gate.get("recommended_commander_action"),
        "l2_approval_recorded": l2_recorded,
        "steps": steps,
        "track_wall": {"prophecy_promotion_gates_touch": False, "a_track_auto_promotion": False},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failed = [s for s in steps if s.get("exit_code") not in (0, None)]
    print(json.dumps({"ok": not failed, "out": str(args.output_json), "failed_steps": [s["step"] for s in failed]}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
