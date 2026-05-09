#!/usr/bin/env python3
"""Check minimum quality gates for public graph response (NON_GATING)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "public_graph_response_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "public_graph_quality_gate_v1_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-nodes", type=int, default=3)
    ap.add_argument("--min-edges", type=int, default=2)
    ap.add_argument("--min-insights", type=int, default=1)
    args = ap.parse_args()

    src = args.input_json if args.input_json.is_absolute() else ROOT / args.input_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    if not src.is_file():
        raise SystemExit(f"Missing --input-json: {src}")

    doc = _read_json(src)
    nodes = doc.get("nodes") if isinstance(doc.get("nodes"), list) else []
    edges = doc.get("edges") if isinstance(doc.get("edges"), list) else []
    insights = doc.get("insights") if isinstance(doc.get("insights"), list) else []
    policy_ok = (
        doc.get("policy_label") == "NON_GATING"
        and doc.get("research_only") is True
        and doc.get("no_trading_advice") is True
    )
    insight_with_non_gating = any("NON_GATING" in str(i.get("insight_summary") or "") for i in insights if isinstance(i, dict))

    checks = {
        "policy_guard_ok": policy_ok,
        "node_count_ok": len(nodes) >= args.min_nodes,
        "edge_count_ok": len(edges) >= args.min_edges,
        "insight_count_ok": len(insights) >= args.min_insights,
        "insight_non_gating_phrase_ok": insight_with_non_gating,
    }
    all_pass = all(bool(v) for v in checks.values())
    payload = {
        "schema": "public_graph_quality_gate_v1",
        "input_json": str(src),
        "counts": {"nodes": len(nodes), "edges": len(edges), "insights": len(insights)},
        "thresholds": {"min_nodes": args.min_nodes, "min_edges": args.min_edges, "min_insights": args.min_insights},
        "checks": checks,
        "all_pass": all_pass,
        "decision": "PASS" if all_pass else "FAIL",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "decision": payload["decision"]}, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
