#!/usr/bin/env python3
"""Post-saturation Logos candidate-edge maintenance ([HYPO] B-track).

Gold + subgraph verify, S1/review packs, L9-L12 readiness — no canonical merge.
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
GOLD = ROOT / "scripts/build_logos_gold_query_eval_report_v1.py"
SUBGRAPH = ROOT / "scripts/Invoke-GraphSubgraphLaneRecommendedChain_v1.ps1"
S1 = ROOT / "scripts/build_logos_s1_shadow_promotion_review_packet_v1.py"
REVIEW_PACK = ROOT / "scripts/build_logos_candidate_edge_human_review_pack_v1.py"
L9L12 = ROOT / "scripts/run_logos_track_l_l9_l12_readiness_v1.py"
HANDOFF = ROOT / "scripts/build_logos_candidate_edge_saturation_handoff_v1.py"
QUEUE = ROOT / "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json"
BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_post_saturation_maintenance_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, timeout: int = 3600) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False, timeout=timeout)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return int(proc.returncode), out if out else err


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _queue_stats() -> dict[str, Any]:
    q = _read_json(QUEUE)
    stats = q.get("stats") if isinstance(q.get("stats"), dict) else {}
    return {
        "total_items": stats.get("total_items"),
        "ann_lite_primary": stats.get("ann_lite_primary"),
        "offline_4d_only": stats.get("offline_4d_only"),
        "pending_count": stats.get("pending_count"),
        "approved_count": stats.get("approved_count"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-l9-l12", action="store_true")
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    exit_code = 0

    for step, cmd, timeout in (
        ("gold_query_eval", [sys.executable, str(GOLD)], 600),
        (
            "subgraph_replay",
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SUBGRAPH),
                "-SkipPetPoC",
                "-SkipDeviceGraphSync",
            ],
            600,
        ),
        ("s1_shadow_packet", [sys.executable, str(S1)], 120),
        ("human_review_pack", [sys.executable, str(REVIEW_PACK)], 120),
    ):
        code, tail = _run(cmd, timeout=timeout)
        steps.append({"step": step, "exit_code": code, "tail": tail[-400:] if len(tail) > 400 else tail})
        if code != 0:
            exit_code = code

    l9_doc: dict[str, Any] = {}
    if exit_code == 0 and not args.skip_l9_l12:
        code, tail = _run([sys.executable, str(L9L12)], timeout=120)
        steps.append({"step": "l9_l12_readiness", "exit_code": code, "tail": tail[-300:] if len(tail) > 300 else tail})
        l9_doc = _read_json(ROOT / "docs/final/artifacts/logos_track_l_l9_l12_readiness_v1_latest.json")
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run([sys.executable, str(HANDOFF)], timeout=60)
        steps.append({"step": "saturation_handoff_pack", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    bundle = _read_json(BUNDLE)
    gf = bundle.get("graph_files") if isinstance(bundle.get("graph_files"), dict) else {}
    gold_doc = _read_json(ROOT / "reports/logos_gold_query_eval_v1_latest.json")
    gold_summary = gold_doc.get("summary") if isinstance(gold_doc.get("summary"), dict) else {}
    gold_pass = gold_summary.get("gold_required_all_pass")

    doc = {
        "schema": "logos_candidate_edge_post_saturation_maintenance_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "exit_code": exit_code,
        "canonical_graph": {
            "nodes_line_count": gf.get("nodes_line_count"),
            "edges_line_count": gf.get("edges_line_count"),
        },
        "gold_required_all_pass": gold_pass,
        "l9_l12_ok": l9_doc.get("l9_l12_ok"),
        "ready_for_external_send": False,
        "queue_stats": _queue_stats(),
        "steps": steps,
    }
    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": exit_code == 0, "edges": gf.get("edges_line_count"), "out": str(out_path)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
