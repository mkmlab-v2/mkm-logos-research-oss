#!/usr/bin/env python3
"""Offline gate: Logos Graph Studio Layer B UX — on-domain React surface + contract.

v2 (2026-07-08): retargeted from the deprecated legacy static ``qa_v2.html`` (ECharts,
CF backup only) to the on-domain React inline demo, which is where the Layer-B
autoplay / citation storyboard UX actually ships. Also asserts the component is
*wired* (imported by a live surface) so it cannot silently regress to orphaned dead
code again. The legacy static markers are recorded in the contract but no longer
required here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/final/artifacts/logos_graph_studio_layer_b_ux_contract_v1.json"
OUT = ROOT / "reports/logos_graph_studio_layer_b_qa_v2_markers_v1_latest.json"

# On-domain React surface that owns the Layer-B UX (autoplay beats + storyboard + mindmap).
REACT_SURFACE = (
    ROOT
    / "projects/no1kmedi/src/components/logos/LogosGraphStudioHeroInlineDemo.tsx"
)
# The live fold that mounts the demo on user-initiated open (<details>).
WIRED_BY = (
    ROOT
    / "projects/no1kmedi/src/components/logos-research/LogosResearchStudioDemoFold.tsx"
)
# Directory scanned to prove the demo component is imported (not orphaned).
WIRE_SCAN_DIR = ROOT / "projects/no1kmedi/src"

REACT_MARKERS = (
    'data-layer-b-embed',
    'data-logos-graph-studio-inline',
    "prefersReducedMotion",
    'role="progressbar"',
    "NON_GATING",
    "LOGOS_HERO_DEMO_BEATS_V1",
)

COMPONENT_NAME = "LogosGraphStudioHeroInlineDemo"


def _is_wired() -> tuple[bool, list[str]]:
    """True if the demo component is imported by a live (non-archive) surface."""
    hits: list[str] = []
    if not WIRE_SCAN_DIR.is_dir():
        return False, hits
    for path in WIRE_SCAN_DIR.rglob("*.tsx"):
        parts = set(path.parts)
        if "_archive" in parts:
            continue
        if path.resolve() == REACT_SURFACE.resolve():
            continue  # skip the component's own definition
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if COMPONENT_NAME in text:
            hits.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    return bool(hits), hits


def main() -> int:
    errors: list[str] = []

    if not CONTRACT.is_file():
        print(f"MISSING: {CONTRACT}", file=sys.stderr)
        return 1
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "logos_graph_studio_layer_b_ux_contract_v1":
        errors.append("contract schema mismatch")
    beats = contract.get("beats_ms") or []
    if len(beats) < 4:
        errors.append("contract beats_ms too short")

    react_markers_missing: list[str] = []
    if not REACT_SURFACE.is_file():
        errors.append(f"react surface missing: {REACT_SURFACE.relative_to(ROOT)}")
    else:
        body = REACT_SURFACE.read_text(encoding="utf-8")
        react_markers_missing = [m for m in REACT_MARKERS if m not in body]
        if react_markers_missing:
            errors.append(f"react markers missing: {react_markers_missing}")

    if not WIRED_BY.is_file():
        errors.append(f"wired-by fold missing: {WIRED_BY.relative_to(ROOT)}")

    wired, wire_hits = _is_wired()
    if not wired:
        errors.append(
            f"{COMPONENT_NAME} is orphaned — not imported by any live surface"
        )

    report = {
        "schema": "logos_graph_studio_layer_b_qa_v2_markers_v1",
        "ok": len(errors) == 0,
        "contract_path": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "react_surface": str(REACT_SURFACE.relative_to(ROOT)).replace("\\", "/"),
        "react_markers_missing": react_markers_missing,
        "wired": wired,
        "wired_by": wire_hits[:5],
        "beat_count": len(beats),
        "legacy_static_deprecated": contract.get("surface_legacy_static"),
        "errors": errors,
        "reproducible_command": "py scripts/check_logos_graph_studio_layer_b_qa_v2_markers_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "out": str(OUT), "errors": errors}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
