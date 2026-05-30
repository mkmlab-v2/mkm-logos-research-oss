#!/usr/bin/env python3
"""Auto chain: offline_4d_knn queue approve → signoff (saturation ack) → gate → pending JSONL.

Does NOT merge into canonical graph unless --include-canonical-merge (human-risk flag).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REVIEW_DECISIONS = ROOT / "scripts/apply_logos_candidate_edge_human_review_decisions_v1.py"
SIGNOFF = ROOT / "scripts/apply_logos_candidate_edge_promotion_signoff_v1.py"
GATE = ROOT / "scripts/check_logos_candidate_edge_promotion_gate_v1.py"
PROMOTE = ROOT / "scripts/promote_logos_candidate_edge_survivors_v1.py"
MERGE_CHAIN = ROOT / "scripts/run_logos_candidate_edge_canonical_merge_chain_v1.py"
PACK = ROOT / "scripts/build_logos_candidate_edge_human_review_pack_v1.py"
SIGNOFF_4D = ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_signoff_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_offline_4d_auto_promote_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return int(proc.returncode), out if out else err


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--approver", default="commander_auto_staging")
    ap.add_argument("--include-canonical-merge", action="store_true")
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    exit_code = 0

    for label, cmd in (
        (
            "review_decisions",
            [
                sys.executable,
                str(REVIEW_DECISIONS),
                "--auto-approve-offline-4d-only",
                "--reviewer",
                args.approver,
            ],
        ),
        (
            "signoff",
            [
                sys.executable,
                str(SIGNOFF),
                "--lane-id",
                "offline_4d_knn",
                "--approver",
                args.approver,
                "--saturation-warning-acknowledged",
            ],
        ),
        (
            "promotion_gate",
            [
                sys.executable,
                str(GATE),
                "--lane-id",
                "offline_4d_knn",
                "--signoff-json",
                str(SIGNOFF_4D),
                "--strict",
            ],
        ),
    ):
        code, tail = _run(cmd)
        steps.append({"step": label, "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code
            break

    if exit_code == 0:
        code, tail = _run([sys.executable, str(PROMOTE), "--lane-id", "offline_4d_knn"])
        steps.append({"step": "promote_pending", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0 and args.include_canonical_merge:
        code, tail = _run([sys.executable, str(MERGE_CHAIN)])
        steps.append({"step": "canonical_merge_chain", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run([sys.executable, str(PACK)])
        steps.append({"step": "refresh_review_pack", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    doc = {
        "schema": "logos_candidate_edge_offline_4d_auto_promote_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "lane_id": "offline_4d_knn",
        "saturation_warning_acknowledged": True,
        "canonical_merge_ran": bool(args.include_canonical_merge),
        "exit_code": exit_code,
        "steps": steps,
        "artifacts": {
            "signoff_json": str(SIGNOFF_4D.relative_to(ROOT)).replace("\\", "/"),
            "pending_jsonl": "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_v1.jsonl",
            "promotion_json": "docs/final/artifacts/logos_candidate_edge_promotion_v1_latest.json",
        },
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
