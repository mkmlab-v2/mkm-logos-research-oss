#!/usr/bin/env python3
"""Chain: human review queue + dual-lane promotion gates ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REVIEW_QUEUE = ROOT / "scripts/build_logos_candidate_edge_human_review_queue_v1.py"
GATE = ROOT / "scripts/check_logos_candidate_edge_promotion_gate_v1.py"
PROMOTE = ROOT / "scripts/promote_logos_candidate_edge_survivors_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_review_promotion_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return int(proc.returncode), out if out else err


def _read_gate(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-review-queue", action="store_true")
    ap.add_argument("--try-promote", action="store_true", help="Attempt promote when gate PASS (signoff required)")
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    exit_code = 0

    if not args.skip_review_queue:
        code, tail = _run([sys.executable, str(REVIEW_QUEUE)])
        steps.append({"step": "human_review_queue", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    gate_paths = {
        "offline_4d_knn": ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_gate_v1_latest.json",
        "ann_lite": ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_gate_ann_lite_v1_latest.json",
    }

    for lane in ("ann_lite", "offline_4d_knn"):
        if exit_code != 0:
            break
        code, tail = _run([sys.executable, str(GATE), "--lane-id", lane])
        steps.append({"step": f"promotion_gate_{lane}", "exit_code": code, "tail": tail})
        gate_doc = _read_gate(gate_paths[lane])
        steps[-1]["gate_pass"] = bool(gate_doc.get("gate_pass"))
        steps[-1]["status"] = gate_doc.get("status")

        if args.try_promote and gate_doc.get("gate_pass"):
            code2, tail2 = _run([sys.executable, str(PROMOTE), "--lane-id", lane])
            steps.append({"step": f"promote_{lane}", "exit_code": code2, "tail": tail2})
            if code2 != 0:
                exit_code = code2

    gates_summary = {
        lane: {
            "gate_pass": bool(_read_gate(gate_paths[lane]).get("gate_pass")),
            "status": _read_gate(gate_paths[lane]).get("status"),
            "survivor_count": _read_gate(gate_paths[lane]).get("survivor_count"),
        }
        for lane in gate_paths
    }

    doc = {
        "schema": "logos_candidate_edge_review_promotion_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "hypothesis_tier": "B",
        "exit_code": exit_code,
        "gates_summary": gates_summary,
        "any_gate_pass": any(g["gate_pass"] for g in gates_summary.values()),
        "steps": steps,
        "artifacts": {
            "review_queue_json": "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json",
            "gate_ann_lite_json": "docs/final/artifacts/logos_candidate_edge_promotion_gate_ann_lite_v1_latest.json",
            "gate_4d_json": "docs/final/artifacts/logos_candidate_edge_promotion_gate_v1_latest.json",
        },
        "blockers_ko": [
            "signoff approved=false — 휴먼 검수 후 lane별 signoff JSON 갱신",
            "4D lane: saturation_warning_acknowledged 필요",
        ],
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
