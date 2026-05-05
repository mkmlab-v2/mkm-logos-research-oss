#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.6}
# Balance: 90
# Purpose: Run extended sweeps for start/expand and summarize best exploratory candidates.
# Keywords: extended sweep, exploratory, top-k, btrack
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def run_sweep(mode: str, out_path: Path, external: Path, internal: Path, node_map: Path) -> dict[str, Any]:
    cmd = [
        "py",
        str(resolve("scripts/sweep_external_baseline_topk_v1.py")),
        "--external-input",
        str(external),
        "--internal-edges-jsonl",
        str(internal),
        "--node-ref-map-json",
        str(node_map),
        "--k-values",
        "50,100,200,500,1000,2000,5000,10000",
        "--range-mode",
        mode,
        "--output-json",
        str(out_path),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or f"sweep failed: {mode}")
    return json.loads(out_path.read_text(encoding="utf-8"))


def pick_best(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    return max(
        rows,
        key=lambda r: (
            float(r.get("delta_random_baseline", 0.0) or 0.0),
            float(r.get("precision_at_k", 0.0) or 0.0),
        ),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Run extended start/expand sweeps and summarize candidates.")
    ap.add_argument("--external-input", default="docs/final/artifacts/external_cross_references_openbible/cross_references.txt")
    ap.add_argument("--internal-edges-jsonl", default="docs/final/artifacts/global_atom_network_core100_edges_latest.jsonl")
    ap.add_argument("--node-ref-map-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    ap.add_argument("--start-output-json", default="docs/final/artifacts/external_bible_crossref_topk_sweep_extended_start_latest.json")
    ap.add_argument("--expand-output-json", default="docs/final/artifacts/external_bible_crossref_topk_sweep_extended_expand_latest.json")
    ap.add_argument("--summary-output-json", default="docs/final/artifacts/external_bible_crossref_extended_sweep_summary_latest.json")
    args = ap.parse_args()

    external = resolve(args.external_input)
    internal = resolve(args.internal_edges_jsonl)
    node_map = resolve(args.node_ref_map_json)
    start_out = resolve(args.start_output_json)
    expand_out = resolve(args.expand_output_json)
    summary_out = resolve(args.summary_output_json)

    d_start = run_sweep("start", start_out, external, internal, node_map)
    d_expand = run_sweep("expand", expand_out, external, internal, node_map)
    b_start = pick_best(d_start.get("rows", []) if isinstance(d_start.get("rows"), list) else [])
    b_expand = pick_best(d_expand.get("rows", []) if isinstance(d_expand.get("rows"), list) else [])

    summary = {
        "schema": "external_bible_crossref_extended_sweep_summary_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "start_sweep_ref": str(start_out),
        "expand_sweep_ref": str(expand_out),
        "best_start": b_start,
        "best_expand": b_expand,
    }
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(summary_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
