#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.5}
# Balance: 90
# Purpose: Sweep top-k values for external baseline overlap parser and summarize metric sensitivity.
# Keywords: sweep, top-k, sensitivity, baseline, precision
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


def run_parser(
    parser_script: Path,
    external_input: Path,
    internal_edges: Path,
    node_map: Path | None,
    top_k: int,
    report_out: Path,
    range_mode: str,
) -> dict[str, Any]:
    cmd = [
        "py",
        str(parser_script),
        "--external-input",
        str(external_input),
        "--internal-edges-jsonl",
        str(internal_edges),
        "--top-k",
        str(top_k),
        "--range-mode",
        range_mode,
        "--report-out-json",
        str(report_out),
    ]
    if node_map is not None:
        cmd.extend(["--node-ref-map-json", str(node_map)])
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"parser failed for k={top_k}: {proc.stderr.strip() or proc.stdout.strip()}")
    return json.loads(report_out.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep top-k sensitivity for external baseline overlap.")
    ap.add_argument("--external-input", default="docs/final/artifacts/external_cross_references_openbible/cross_references.txt")
    ap.add_argument("--internal-edges-jsonl", default="docs/final/artifacts/global_atom_network_core100_edges_latest.jsonl")
    ap.add_argument("--node-ref-map-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    ap.add_argument("--k-values", default="100,500,1000,5000")
    ap.add_argument("--range-mode", choices=["start", "expand"], default="start")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_topk_sweep_latest.json")
    args = ap.parse_args()

    parser_script = resolve("scripts/parse_external_baseline_v1.py")
    external_input = resolve(args.external_input)
    internal_edges = resolve(args.internal_edges_jsonl)
    node_map_path = resolve(args.node_ref_map_json) if str(args.node_ref_map_json).strip() else None
    output_path = resolve(args.output_json)
    if not parser_script.is_file():
        raise SystemExit(f"missing parser script: {parser_script}")
    if not external_input.is_file():
        raise SystemExit(f"missing external input: {external_input}")
    if not internal_edges.is_file():
        raise SystemExit(f"missing internal edges: {internal_edges}")
    if node_map_path is not None and not node_map_path.is_file():
        raise SystemExit(f"missing node map json: {node_map_path}")

    k_values = [int(x.strip()) for x in str(args.k_values).split(",") if x.strip()]
    if not k_values:
        raise SystemExit("k-values must include at least one integer")

    rows = []
    tmp_report = resolve("docs/final/artifacts/_tmp_external_baseline_topk_report_v1.json")
    for k in k_values:
        doc = run_parser(
            parser_script=parser_script,
            external_input=external_input,
            internal_edges=internal_edges,
            node_map=node_map_path,
            top_k=max(1, int(k)),
            report_out=tmp_report,
            range_mode=args.range_mode,
        )
        m = doc.get("metrics", {}) if isinstance(doc.get("metrics"), dict) else {}
        c = doc.get("counts", {}) if isinstance(doc.get("counts"), dict) else {}
        rows.append(
            {
                "top_k": int(k),
                "coverage_overlap": float(m.get("coverage_overlap", 0.0) or 0.0),
                "precision_at_k": float(m.get("precision_at_k", 0.0) or 0.0),
                "delta_random_baseline": float(m.get("delta_random_baseline", 0.0) or 0.0),
                "overlap_pair_count": int(c.get("overlap_pair_count", 0) or 0),
            }
        )

    out = {
        "schema": "external_bible_crossref_topk_sweep_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "baseline_classification": "manual_editorial_heuristic",
        "algorithmic_ground_truth": False,
        "inputs": {
            "external_input": str(external_input),
            "internal_edges_jsonl": str(internal_edges),
            "node_ref_map_json": str(node_map_path) if node_map_path else None,
            "range_mode": args.range_mode,
            "k_values": k_values,
        },
        "rows": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
