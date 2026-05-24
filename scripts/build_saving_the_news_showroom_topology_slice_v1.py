#!/usr/bin/env python3
"""Saving the News — showroom topology snapshot + matrix panel slice (B-track [HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.saving_the_news_public_copy_facade_v1 import (  # noqa: E402
    DISPLAY_INTERNAL,
    DISPLAY_PUBLIC,
    PUBLIC_UI,
    apply_public_facade_to_panel,
)

ART = ROOT / "docs" / "final" / "artifacts"
MATRIX = ART / "saving_the_news_phase2_matrix_view_v1_latest.json"
GATING = ART / "saving_the_news_phase3_truth_gating_v1_latest.json"
APPENDIX = ART / "saving_the_news_perspective_appendix_v1_latest.json"
FLYWHEEL = ART / "saving_the_news_flywheel_as_snapshot_v1_latest.json"
OUT_TOPOLOGY = ART / "saving_the_news_showroom_topology_slice_v1_latest.json"
OUT_PANEL = ART / "saving_the_news_matrix_panel_slice_v1_latest.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_topology_snapshot(
    matrix: dict[str, Any],
    gating: dict[str, Any] | None,
    *,
    stale_hours: int,
    display_mode: str,
) -> dict[str, Any]:
    now = _utc_now()
    gen = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    stale = (now + timedelta(hours=stale_hours)).replace(microsecond=0)
    stale_s = stale.isoformat().replace("+00:00", "Z")

    fa = matrix.get("final_action") or {}
    action = str(fa.get("action", "WATCH"))
    cr = matrix.get("conflict_resolver") or {}
    anchor = matrix.get("headline_anchor") or {}
    headline = str(anchor.get("headline", ""))[:120]

    refs = [
        _display_path(MATRIX),
        _display_path(ART / "saving_the_news_phase3_truth_gating_v1_latest.json"),
        _display_path(ART / "saving_the_news_public_event_ingest_stub_v1.json"),
        _display_path(ART / "saving_the_news_news_rt_bench_result_v1_latest.json"),
        _display_path(APPENDIX),
        _display_path(FLYWHEEL),
        "docs/research/saving_the_news_blueprint_v1.md",
    ]

    if display_mode == DISPLAY_PUBLIC:
        summary = (
            f"Multi-signal observability · posture={action} · conflict={cr.get('conflict')} · "
            f"{headline or 'no headline'} — observation only, not investment advice."
        )[:500]
        hypo_banner = PUBLIC_UI["banner"]
    else:
        summary = (
            f"Saving the News matrix panel · Final={action} · conflict={cr.get('conflict')} · "
            f"{headline or 'no headline'} — not investment advice."
        )[:500]
        hypo_banner = "[HYPO] Saving the News — Multi-Lens matrix observability (research_only)"

    return {
        "schema_version": "showroom_topology_radar_snapshot_v1",
        "generated_at_utc": gen,
        "stale_after_utc": stale_s,
        "display_mode": display_mode,
        "hypo_banner": hypo_banner,
        "summary_one_line": summary,
        "artifact_refs": refs[:32],
        "disclaimer_ref": "PUBLIC_FACING_v1.7_saving_the_news",
        "no_trade_signals": True,
    }


def build_matrix_panel(
    matrix: dict[str, Any],
    gating: dict[str, Any] | None,
    appendix: dict[str, Any] | None,
    flywheel: dict[str, Any] | None,
) -> dict[str, Any]:
    now = _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    pub = (gating or {}).get("publish_signoff") or {}
    layer_b = None
    if appendix:
        layer_b = {
            "bridge_mode": appendix.get("bridge_mode"),
            "coordinator_brief_ko": appendix.get("coordinator_brief_ko"),
            "entity_tokens": appendix.get("entity_tokens", []),
            "perspective_slots": appendix.get("perspective_slots", []),
            "appendix_ref": _display_path(APPENDIX),
            "flywheel_as_ref": appendix.get("flywheel_as_ref"),
            "hypo_tags": ["[HYPO]", "[NON_GATING] where applicable"],
        }
    return {
        "schema": "saving_the_news_matrix_panel_slice_v1",
        "display_mode": DISPLAY_INTERNAL,
        "lane": "research_only",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "generated_at_utc": now,
        "field": matrix.get("field"),
        "headline_anchor": matrix.get("headline_anchor"),
        "matrix_rows": matrix.get("matrix_rows", []),
        "external_channel_metaphor": matrix.get("external_channel_metaphor", []),
        "external_channel_disclaimer": matrix.get("external_channel_disclaimer"),
        "conflict_resolver": matrix.get("conflict_resolver"),
        "final_action": matrix.get("final_action"),
        "output_order": matrix.get("output_order"),
        "publish_signoff": pub,
        "layer_b": layer_b,
        "flywheel_as_axes": (flywheel or {}).get("axes", []),
        "topology_snapshot_ref": _display_path(OUT_TOPOLOGY),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stale-hours", type=int, default=24)
    ap.add_argument("--fail-if-missing", action="store_true")
    ap.add_argument(
        "--display-mode",
        choices=[DISPLAY_INTERNAL, DISPLAY_PUBLIC],
        default=DISPLAY_PUBLIC,
        help="public_showroom applies engineering copy facade (default for staging/VPS)",
    )
    args = ap.parse_args()

    matrix = _read(MATRIX)
    if not matrix:
        print(f"Missing matrix: {MATRIX}")
        return 2 if args.fail_if_missing else 0

    gating = _read(GATING)
    appendix = _read(APPENDIX)
    flywheel = _read(FLYWHEEL)
    topo = build_topology_snapshot(matrix, gating, stale_hours=args.stale_hours, display_mode=args.display_mode)
    panel = build_matrix_panel(matrix, gating, appendix, flywheel)
    if args.display_mode == DISPLAY_PUBLIC:
        panel = apply_public_facade_to_panel(panel)

    ART.mkdir(parents=True, exist_ok=True)
    OUT_TOPOLOGY.write_text(json.dumps(topo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_PANEL.write_text(json.dumps(panel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_TOPOLOGY.name} and {OUT_PANEL.name} display_mode={args.display_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
