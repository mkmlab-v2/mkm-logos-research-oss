#!/usr/bin/env python3
"""Build Field×Logos overlay prophecy artifact (B-track, NON_GATING)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from field_logos_overlay_prophecy_common_v1 import (  # noqa: E402
    DEFAULT_FIELD_SNAPSHOT,
    DEFAULT_HOLDOUT,
    DEFAULT_LOGOS_RESONANCE,
    DEFAULT_OVERLAY_OUT,
    SCHEMA,
    VERSION,
    fused_confidence,
    load_holdout_items,
    pick_regime_resonance_row,
    read_json,
    rel_path,
    router_bridge_artifacts,
    router_top_match_score,
)

ROUTER = ROOT / "scripts/run_logos_subgraph_graphrag_router_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_router(query: str, *, top_bridges: int, out_path: Path) -> dict[str, Any] | None:
    if not ROUTER.is_file():
        return None
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query",
            query,
            "--top-bridges",
            str(top_bridges),
            "--output-json",
            str(out_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if cp.returncode != 0 or not out_path.is_file():
        return None
    return read_json(out_path)


def build_overlay(
    *,
    field_snapshot_path: Path,
    logos_resonance_path: Path,
    holdout_path: Path,
    overlay_weight: float,
    theme_match_threshold: float,
    logos_resonance_min_cosine: float,
    top_bridges: int,
) -> dict[str, Any]:
    field_doc = read_json(field_snapshot_path)
    shadow = read_json(logos_resonance_path)
    field_layer = (field_doc or {}).get("field_layer") if isinstance((field_doc or {}).get("field_layer"), dict) else {}
    primary_regime = field_layer.get("primary_regime_id_observational")
    resonance_row, resonance_regime, resonance_cosine = pick_regime_resonance_row(shadow, primary_regime)

    predictions: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="field_logos_router_") as td:
        tmp = Path(td)
        for idx, item in enumerate(load_holdout_items(holdout_path)):
            query = str(item["query_ko"])
            pid = str(item.get("id") or f"p{idx+1}")
            router_out = tmp / f"router_{pid}.json"
            router = _run_router(query, top_bridges=top_bridges, out_path=router_out)
            top_score = router_top_match_score(router)
            bridges = router_bridge_artifacts(router)
            lanes = list(router.get("theme_lanes_active") or []) if router else []
            conf = fused_confidence(
                overlay_weight=overlay_weight,
                router_top_score=top_score,
                resonance_cosine=resonance_cosine,
                theme_match_threshold=theme_match_threshold,
            )
            field_ok = resonance_cosine is None or resonance_cosine >= logos_resonance_min_cosine
            predictions.append(
                {
                    "prediction_id": pid,
                    "query_ko": query,
                    "field_axis": {
                        "primary_regime_id_observational": primary_regime,
                        "resonance_regime": resonance_regime,
                        "resonance_cosine": resonance_cosine,
                        "field_alignment_ok": field_ok,
                    },
                    "logos_axis": {
                        "bridges_matched": int(router.get("bridges_matched") or 0) if router else 0,
                        "bridge_artifacts": bridges,
                        "theme_lanes_active": lanes,
                        "top_match_score": top_score,
                        "verse_ids": list(router.get("verse_ids") or []) if router else [],
                    },
                    "fused_hypothesis": {
                        "narrative_tag_ko": (
                            f"Field={primary_regime or 'unknown'} × Logos overlay "
                            f"(lanes={','.join(lanes) or 'none'})"
                        ),
                        "confidence_0_1": conf,
                        "hypothesis_tier": "[HYPO]",
                        "research_only": True,
                        "non_gating": True,
                    },
                    "router_summary": {
                        "paths": len(router.get("paths") or []) if router else 0,
                        "router_schema": router.get("schema") if router else None,
                    },
                }
            )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "non_gating": True,
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
            "field_primary_logos_secondary": True,
        },
        "parameters": {
            "overlay_weight": overlay_weight,
            "theme_match_threshold": theme_match_threshold,
            "logos_resonance_min_cosine": logos_resonance_min_cosine,
        },
        "field_observation": {
            "primary_regime_id_observational": primary_regime,
            "primary_source": field_layer.get("primary_source"),
            "snapshot_path": rel_path(field_snapshot_path) if field_doc else None,
        },
        "logos_overlay": {
            "resonance_shadow_path": rel_path(logos_resonance_path) if shadow else None,
            "regime_resonance_row": resonance_row,
            "best_regime_from_shadow": resonance_regime,
            "top_hit_cosine": resonance_cosine,
        },
        "predictions": predictions,
        "evidence_paths": {
            "field_snapshot": rel_path(field_snapshot_path),
            "logos_resonance_shadow": rel_path(logos_resonance_path),
            "holdout_fixture": rel_path(holdout_path),
            "router_script": rel_path(ROUTER),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--field-snapshot-json", type=Path, default=DEFAULT_FIELD_SNAPSHOT)
    ap.add_argument("--logos-resonance-json", type=Path, default=DEFAULT_LOGOS_RESONANCE)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OVERLAY_OUT)
    ap.add_argument("--overlay-weight", type=float, default=0.35)
    ap.add_argument("--theme-match-threshold", type=float, default=0.5)
    ap.add_argument("--logos-resonance-min-cosine", type=float, default=0.0)
    ap.add_argument("--top-bridges", type=int, default=3)
    args = ap.parse_args()

    doc = build_overlay(
        field_snapshot_path=args.field_snapshot_json if args.field_snapshot_json.is_absolute() else ROOT / args.field_snapshot_json,
        logos_resonance_path=args.logos_resonance_json if args.logos_resonance_json.is_absolute() else ROOT / args.logos_resonance_json,
        holdout_path=args.holdout_json if args.holdout_json.is_absolute() else ROOT / args.holdout_json,
        overlay_weight=float(args.overlay_weight),
        theme_match_threshold=float(args.theme_match_threshold),
        logos_resonance_min_cosine=float(args.logos_resonance_min_cosine),
        top_bridges=int(args.top_bridges),
    )
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "predictions": len(doc.get("predictions") or []),
                "primary_regime": doc.get("field_observation", {}).get("primary_regime_id_observational"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
