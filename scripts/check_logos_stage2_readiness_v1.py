#!/usr/bin/env python3
"""Stage-2 readiness gate for Logos enhancement pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_ONTOLOGY = ART / "logos_ontology_registry_v1_latest.json"
DEFAULT_SELECTED = ART / "logos_response_v1_retry_selected_latest.json"
DEFAULT_GRAPH_GATE = ART / "public_graph_quality_gate_v1_latest.json"
DEFAULT_OUT = ART / "logos_stage2_readiness_v1_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ontology-json", type=Path, default=DEFAULT_ONTOLOGY)
    ap.add_argument("--selected-json", type=Path, default=DEFAULT_SELECTED)
    ap.add_argument("--graph-gate-json", type=Path, default=DEFAULT_GRAPH_GATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-rules", type=int, default=4)
    ap.add_argument("--min-verified-ratio", type=float, default=0.8)
    args = ap.parse_args()

    ontology_path = args.ontology_json if args.ontology_json.is_absolute() else ROOT / args.ontology_json
    selected_path = args.selected_json if args.selected_json.is_absolute() else ROOT / args.selected_json
    graph_gate_path = args.graph_gate_json if args.graph_gate_json.is_absolute() else ROOT / args.graph_gate_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    for p in (ontology_path, selected_path, graph_gate_path):
        if not p.is_file():
            raise SystemExit(f"Missing required input: {p}")

    ontology = _read_json(ontology_path)
    selected = _read_json(selected_path)
    graph_gate = _read_json(graph_gate_path)

    relations = ontology.get("relations") if isinstance(ontology.get("relations"), list) else []
    roots = (
        ontology.get("entities", {}).get("morphology_roots")
        if isinstance(ontology.get("entities"), dict)
        else []
    )
    roots = roots if isinstance(roots, list) else []
    verified = sum(1 for r in roots if isinstance(r, dict) and r.get("verification_status") == "verified")
    verified_ratio = float(verified / len(roots)) if roots else 0.0

    trace = selected.get("ontology_trace") if isinstance(selected.get("ontology_trace"), dict) else {}
    checks = {
        "rules_count_ok": len(relations) >= args.min_rules,
        "verified_roots_ratio_ok": verified_ratio >= args.min_verified_ratio,
        "public_graph_quality_pass": bool(graph_gate.get("all_pass") is True),
        "selected_has_ontology_trace": bool(trace),
        "selected_trace_non_gating_ok": bool(trace.get("non_gating_only") is True and trace.get("price_mapping_forbidden") is True),
    }
    all_pass = all(checks.values())
    payload = {
        "schema": "logos_stage2_readiness_v1",
        "inputs": {
            "ontology_json": str(ontology_path),
            "selected_json": str(selected_path),
            "graph_gate_json": str(graph_gate_path),
        },
        "metrics": {
            "rules_count": len(relations),
            "morph_roots_count": len(roots),
            "morph_verified_roots_count": verified,
            "morph_verified_ratio": round(verified_ratio, 6),
        },
        "thresholds": {
            "min_rules": args.min_rules,
            "min_verified_ratio": args.min_verified_ratio,
        },
        "checks": checks,
        "all_pass": all_pass,
        "decision": "STAGE2_READY" if all_pass else "STAGE2_NOT_READY",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": payload["decision"]}, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
