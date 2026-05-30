#!/usr/bin/env python3
"""LoRA prune spike: strict survivor re-select (non-destructive) + lane compare + Track L L1.

Does NOT overwrite production survivors or canonical graph. [HYPO] B-track research_only.
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

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from logos_candidate_edge_lane_common_v1 import undirected_pair_key

SELECT = ROOT / "scripts/select_logos_candidate_edge_survivors_v1.py"
COMPARE = ROOT / "scripts/compare_logos_candidate_edge_lanes_v1.py"
L1 = ROOT / "scripts/run_logos_track_l_l1_readiness_v1.py"
GOLD = ROOT / "scripts/build_logos_gold_query_eval_report_v1.py"

SPIKE_SURV = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_lora_prune_spike_v1_latest.json"
SPIKE_PRUNED = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_survivors_lora_prune_spike_v1.jsonl"
PROD_SURV = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json"
CANONICAL = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_lora_prune_spike_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return int(proc.returncode), out if out else err


def _canonical_pairs() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    if not CANONICAL.is_file():
        return pairs
    for line in CANONICAL.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        src = str(row.get("src_node_id") or "")
        dst = str(row.get("dst_node_id") or "")
        if src and dst:
            pairs.add(undirected_pair_key(src, dst))
    return pairs


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-n", type=int, default=200)
    ap.add_argument("--max-per-src", type=int, default=1)
    ap.add_argument("--max-cosine", type=float, default=0.998)
    ap.add_argument("--min-cosine", type=float, default=0.92)
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    exit_code = 0

    prod = _load_json(PROD_SURV)
    prod_count = int((prod.get("stats") or {}).get("survivor_count") or len(prod.get("survivors") or []))

    code, tail = _run(
        [
            sys.executable,
            str(SELECT),
            "--top-n",
            str(int(args.top_n)),
            "--max-per-src",
            str(int(args.max_per_src)),
            "--max-cosine",
            str(float(args.max_cosine)),
            "--min-cosine",
            str(float(args.min_cosine)),
            "--output-json",
            str(SPIKE_SURV),
            "--pruned-jsonl-out",
            str(SPIKE_PRUNED),
        ]
    )
    steps.append({"step": "lora_prune_select", "exit_code": code, "tail": tail})
    if code != 0:
        exit_code = code

    spike = _load_json(SPIKE_SURV)
    spike_count = int((spike.get("stats") or {}).get("survivor_count") or 0)
    canonical = _canonical_pairs()
    net_new = 0
    for row in spike.get("survivors") or []:
        src = str(row.get("src_node_id") or "")
        dst = str(row.get("dst_node_id") or "")
        if src and dst and undirected_pair_key(src, dst) not in canonical:
            net_new += 1

    if exit_code == 0:
        code, tail = _run([sys.executable, str(COMPARE)])
        steps.append({"step": "lane_compare", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run([sys.executable, str(L1)])
        steps.append({"step": "track_l_l1_readiness", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run([sys.executable, str(GOLD)])
        steps.append({"step": "gold_query_eval", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    l1_doc = _load_json(ROOT / "docs/final/artifacts/logos_track_l_l1_readiness_v1_latest.json")
    compare_doc = _load_json(ROOT / "docs/final/artifacts/logos_candidate_edge_lane_compare_v1_latest.json")

    doc = {
        "schema": "logos_candidate_edge_lora_prune_spike_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "prune_params": {
            "top_n": int(args.top_n),
            "max_per_src": int(args.max_per_src),
            "max_cosine": float(args.max_cosine),
            "min_cosine": float(args.min_cosine),
        },
        "survivor_counts": {
            "production_offline_4d": prod_count,
            "lora_prune_spike": spike_count,
            "reduction_vs_production": prod_count - spike_count,
            "net_new_vs_canonical": net_new,
            "canonical_pair_count": len(canonical),
        },
        "lane_compare_recommendation": compare_doc.get("recommendation"),
        "track_l_l1_ok": bool(l1_doc.get("l1_ok")),
        "exit_code": exit_code,
        "steps": steps,
        "artifacts": {
            "spike_survivors_json": str(SPIKE_SURV.relative_to(ROOT)).replace("\\", "/"),
            "spike_pruned_jsonl": str(SPIKE_PRUNED.relative_to(ROOT)).replace("\\", "/"),
            "production_survivors_json": str(PROD_SURV.relative_to(ROOT)).replace("\\", "/"),
            "lane_compare_json": "docs/final/artifacts/logos_candidate_edge_lane_compare_v1_latest.json",
            "track_l_l1_json": "docs/final/artifacts/logos_track_l_l1_readiness_v1_latest.json",
        },
        "disclaimer_ko": (
            "스파이크 산출물은 연구용 별도 경로. canonical·production survivor JSON 덮어쓰지 않음."
        ),
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
