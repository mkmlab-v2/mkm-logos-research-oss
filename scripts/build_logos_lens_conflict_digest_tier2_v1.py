#!/usr/bin/env python3
"""Logos lens Tier2 — conflict digest (NON_GATING exposition only) [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_GRAPHRAG = ROOT / "reports/logos_graphrag_kospi9000_excess_v1_latest.json"
DEFAULT_CROSSWALK = ROOT / "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_LENS = ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_lens_conflict_digest_tier2_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/logos_lens_conflict_digest_tier2_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _top_paths(graphrag: dict[str, Any] | None, *, limit: int = 4) -> list[dict[str, Any]]:
    paths = graphrag.get("paths") if isinstance(graphrag, dict) else []
    if not isinstance(paths, list):
        return []
    ranked = sorted(
        [p for p in paths if isinstance(p, dict)],
        key=lambda p: int(p.get("match_score") or 0),
        reverse=True,
    )
    out: list[dict[str, Any]] = []
    for p in ranked[:limit]:
        steps = p.get("steps") if isinstance(p.get("steps"), list) else []
        out.append(
            {
                "path_id": p.get("path_id"),
                "match_score": p.get("match_score"),
                "verse_tail": steps[-1] if steps else None,
                "note_ko": p.get("note_ko"),
            }
        )
    return out


def build_logos_tier2(
    *,
    graphrag: dict[str, Any] | None,
    crosswalk: dict[str, Any] | None,
    fusion: dict[str, Any] | None,
    lens: dict[str, Any] | None,
) -> dict[str, Any]:
    fusion = fusion or {}
    res = fusion.get("fusion_resolution") if isinstance(fusion.get("fusion_resolution"), dict) else {}
    conflicts = res.get("conflict_ids") if isinstance(res.get("conflict_ids"), list) else []
    logos_lens = (fusion.get("lenses") or {}).get("logos") if isinstance(fusion.get("lenses"), dict) else {}
    scores = (lens or {}).get("scores") if isinstance((lens or {}).get("scores"), dict) else {}
    return {
        "schema": "logos_lens_conflict_digest_tier2_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "lens_id": "logos",
        "gating_weight": 0.0,
        "tier2_role": "conflict_surface_exposition",
        "direction_sign": logos_lens.get("direction_sign") or "bear",
        "direction_score": scores.get("direction_score"),
        "confidence": scores.get("confidence"),
        "conflict_ids": conflicts,
        "excess_unwind_routes": _top_paths(graphrag),
        "crosswalk_pointer": (crosswalk or {}).get("schema"),
        "advisory_ko": (
            "Logos Tier2: excess_unwind·prudence route만 노출. "
            "Field bear와 충돌 시 direction flip 금지·해설만."
        ),
        "forbidden": ["auto_direction_flip", "track_a_merge", "live_order_trigger"],
        "send_gate": "HOLD",
        "pointers": {
            "graphrag": "reports/logos_graphrag_kospi9000_excess_v1_latest.json",
            "crosswalk": "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graphrag-json", type=Path, default=DEFAULT_GRAPHRAG)
    ap.add_argument("--crosswalk-json", type=Path, default=DEFAULT_CROSSWALK)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_logos_tier2(
        graphrag=_read(args.graphrag_json),
        crosswalk=_read(args.crosswalk_json),
        fusion=_read(args.fusion_json),
        lens=_read(args.lens_json),
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "routes": len(doc["excess_unwind_routes"]), "conflicts": len(doc["conflict_ids"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
