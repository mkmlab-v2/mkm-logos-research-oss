#!/usr/bin/env python3
"""Recommended Logos candidate-edge wave ([HYPO] B-track).

Order:
  1) Triage refresh
  2) Covenant convergence commander pack
  3) ANN-lite canonical merge (idempotent) + verify
  4) LoRA strict spike refresh → net-new pending (≤18) → canonical merge + verify

Does NOT bulk-promote offline_4d 500.
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

TRIAGE = ROOT / "scripts/run_logos_candidate_edge_review_triage_v1.py"
COVENANT_PACK = ROOT / "scripts/build_logos_covenant_convergence_review_pack_v1.py"
ANN_MERGE = ROOT / "scripts/run_logos_candidate_edge_ann_lite_canonical_merge_chain_v1.py"
LORA_SPIKE = ROOT / "scripts/run_logos_candidate_edge_lora_prune_spike_v1.py"
NETNEW = ROOT / "scripts/build_logos_lora_spike_netnew_pending_v1.py"
MERGE = ROOT / "scripts/apply_logos_approved_pending_to_canonical_v1.py"
GOLD = ROOT / "scripts/build_logos_gold_query_eval_report_v1.py"
SUBGRAPH = ROOT / "scripts/Invoke-GraphSubgraphLaneRecommendedChain_v1.ps1"

NETNEW_PENDING = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_lora_netnew_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_recommended_wave_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, timeout: int = 3600) -> tuple[int, str]:
    proc = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, check=False, timeout=timeout
    )
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-triage", action="store_true")
    ap.add_argument("--skip-ann-lite-merge", action="store_true")
    ap.add_argument("--skip-offline-4d-batch", action="store_true")
    ap.add_argument("--netnew-max", type=int, default=18)
    ap.add_argument("--lora-top-n", type=int, default=200)
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    exit_code = 0

    if not args.skip_triage:
        code, tail = _run([sys.executable, str(TRIAGE)])
        steps.append({"step": "triage", "exit_code": code, "tail": tail[-300:] if len(tail) > 300 else tail})
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run([sys.executable, str(COVENANT_PACK)])
        steps.append({"step": "covenant_review_pack", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0 and not args.skip_ann_lite_merge:
        code, tail = _run([sys.executable, str(ANN_MERGE)], timeout=600)
        steps.append({"step": "ann_lite_canonical_merge", "exit_code": code, "tail": tail[-400:] if len(tail) > 400 else tail})
        if code != 0:
            exit_code = code

    netnew_report: dict[str, Any] = {}
    merge_report: dict[str, Any] = {}

    if exit_code == 0 and not args.skip_offline_4d_batch:
        code, tail = _run(
            [
                sys.executable,
                str(LORA_SPIKE),
                "--top-n",
                str(int(args.lora_top_n)),
            ],
            timeout=3600,
        )
        steps.append({"step": "lora_prune_spike_refresh", "exit_code": code, "tail": tail[-200:] if len(tail) > 200 else tail})
        if code != 0:
            exit_code = code

        netnew_pending = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_lora_netnew_v1.jsonl"
        full_spike_surv = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_full_corpus_spike_v1_latest.json"
        full_netnew_pending = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_full_corpus_netnew_v1.jsonl"

        if exit_code == 0:
            code, tail = _run(
                [
                    sys.executable,
                    str(NETNEW),
                    "--max-items",
                    str(int(args.netnew_max)),
                ]
            )
            steps.append({"step": "lora_netnew_pending", "exit_code": code, "tail": tail})
            netnew_report = _read_json(ROOT / "docs/final/artifacts/logos_lora_spike_netnew_pending_v1_latest.json")
            pending_for_merge = netnew_pending if code == 0 else None

            if code != 0:
                steps[-1]["note"] = "lora net-new empty — try full-corpus spike survivors"
                code_fc, tail_fc = _run([sys.executable, str(ROOT / "scripts/run_logos_candidate_edges_offline_knn_full_corpus_spike_v1.py")], timeout=3600)
                steps.append({"step": "full_corpus_spike_refresh", "exit_code": code_fc, "tail": tail_fc[-200:] if len(tail_fc) > 200 else tail_fc})
                if code_fc == 0:
                    code_fc2, tail_fc2 = _run(
                        [
                            sys.executable,
                            str(NETNEW),
                            "--spike-survivors-json",
                            str(full_spike_surv),
                            "--max-items",
                            str(int(args.netnew_max)),
                            "--pending-jsonl-out",
                            str(full_netnew_pending),
                            "--report-json",
                            str(ROOT / "docs/final/artifacts/logos_full_corpus_spike_netnew_pending_v1_latest.json"),
                        ]
                    )
                    steps.append({"step": "full_corpus_netnew_pending", "exit_code": code_fc2, "tail": tail_fc2})
                    netnew_report = _read_json(ROOT / "docs/final/artifacts/logos_full_corpus_spike_netnew_pending_v1_latest.json")
                    pending_for_merge = full_netnew_pending if code_fc2 == 0 else None
                    if code_fc2 != 0:
                        steps[-1]["note"] = "no net-new pairs vs canonical — skip merge"

            if pending_for_merge and pending_for_merge.is_file():
                code2, tail2 = _run(
                    [
                        sys.executable,
                        str(MERGE),
                        "--acknowledge-canonical-risk",
                        "--refresh-bundle",
                        "--pending-jsonl",
                        str(pending_for_merge),
                    ]
                )
                steps.append({"step": "canonical_merge_netnew_batch", "exit_code": code2, "tail": tail2})
                merge_report = _read_json(ROOT / "docs/final/artifacts/logos_candidate_edge_canonical_merge_v1_latest.json")
                if code2 != 0:
                    exit_code = code2
                else:
                    code3, tail3 = _run([sys.executable, str(GOLD)])
                    steps.append({"step": "gold_query_eval", "exit_code": code3, "tail": tail3[-300:] if len(tail3) > 300 else tail3})
                    if code3 != 0:
                        exit_code = code3
                    code4, tail4 = _run(
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
                        timeout=600,
                    )
                    steps.append(
                        {
                            "step": "subgraph_replay",
                            "exit_code": code4,
                            "tail": tail4[-400:] if len(tail4) > 400 else tail4,
                        }
                    )
                    if code4 != 0:
                        exit_code = code4

    bundle = _read_json(ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json")
    gf = bundle.get("graph_files") if isinstance(bundle.get("graph_files"), dict) else {}

    doc = {
        "schema": "logos_candidate_edge_recommended_wave_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "bulk_offline_4d_blocked": True,
        "exit_code": exit_code,
        "netnew_batch": {
            "max_items": int(args.netnew_max),
            "selected": netnew_report.get("netnew_selected"),
            "skipped_duplicate": netnew_report.get("skipped_duplicate_vs_canonical"),
            "merge_appended": merge_report.get("appended_count"),
            "canonical_pairs_after": merge_report.get("canonical_pairs_after"),
        },
        "canonical_graph": {
            "nodes_line_count": gf.get("nodes_line_count"),
            "edges_line_count": gf.get("edges_line_count"),
        },
        "artifacts": {
            "covenant_review_pack_md": "reports/logos_covenant_convergence_review_pack_v1_latest.md",
            "triage_md": "reports/logos_candidate_edge_review_triage_v1_latest.md",
            "netnew_pending_jsonl": "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_lora_netnew_v1.jsonl",
        },
        "steps": steps,
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
