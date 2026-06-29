#!/usr/bin/env python3
"""Offline gate: Logos Graph Studio Layer B UX markers in qa_v2 HTML + contract JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "public_showroom_meaning_topology_qa_v2.html"
)
CONTRACT = ROOT / "docs/final/artifacts/logos_graph_studio_layer_b_ux_contract_v1.json"
OUT = ROOT / "reports/logos_graph_studio_layer_b_qa_v2_markers_v1_latest.json"

HTML_MARKERS = (
    "runB2bAutoplayTimeline",
    "applyEmbedMode",
    "layerBB2bTimeline",
    "embed-hero",
    "citation-reveal",
    "citation-lock-badge",
    "b2bAutoplayBar",
    "data-layer-b-contract",
    "logos_graph_studio_layer_b_ux_contract_v1",
    "maybeStartAutoplayAfterReveal",
    "prefersReducedMotion",
)


def main() -> int:
    errors: list[str] = []
    if not HTML.is_file():
        print(f"MISSING: {HTML}", file=sys.stderr)
        return 1
    if not CONTRACT.is_file():
        print(f"MISSING: {CONTRACT}", file=sys.stderr)
        return 1

    body = HTML.read_text(encoding="utf-8")
    missing = [m for m in HTML_MARKERS if m not in body]
    if missing:
        errors.append(f"html markers missing: {missing}")

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "logos_graph_studio_layer_b_ux_contract_v1":
        errors.append("contract schema mismatch")
    beats = contract.get("beats_ms") or []
    if len(beats) < 4:
        errors.append("contract beats_ms too short")

    report = {
        "schema": "logos_graph_studio_layer_b_qa_v2_markers_v1",
        "ok": len(errors) == 0,
        "html_path": str(HTML.relative_to(ROOT)).replace("\\", "/"),
        "contract_path": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "html_markers_missing": missing,
        "beat_count": len(beats),
        "errors": errors,
        "reproducible_command": "py scripts/check_logos_graph_studio_layer_b_qa_v2_markers_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "out": str(OUT), "errors": errors}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
