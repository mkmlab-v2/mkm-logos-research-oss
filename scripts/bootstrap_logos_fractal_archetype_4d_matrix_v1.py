#!/usr/bin/env python3
"""Bootstrap logos_fractal_archetype_4d_matrix_v1.json when missing (B-track research only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "logos_fractal_archetype_4d_matrix_v1.json"
DEFAULT_REFIT = ART / "logos_fractal_archetype_refit_latest.json"


def _default_lexicon() -> dict[str, list[str]]:
    return {
        "S_positive": ["confidence", "stability", "trust", "conviction"],
        "S_negative": ["fear", "panic", "uncertainty", "doubt"],
        "L_positive": ["order", "rule", "policy", "framework", "coordination"],
        "L_negative": ["chaos", "disorder", "fragmentation", "policy vacuum"],
        "K_positive": ["breakout", "inflection", "regime shift", "catalyst"],
        "K_negative": ["stagnation", "plateau", "delay"],
        "M_positive": ["risk-on", "liquidity", "inflow", "expansion"],
        "M_negative": ["risk-off", "outflow", "stress", "drawdown", "volatility"],
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_matrix(*, refit_json: Path = DEFAULT_REFIT) -> dict[str, Any]:
    archetypes: list[dict[str, Any]] = [
        {"id": "creation", "label_ko": "창조", "vector_slkm": {"S": 0.7, "L": 0.85, "K": 0.76, "M": 1.0}},
        {"id": "wilderness", "label_ko": "광야", "vector_slkm": {"S": 0.85, "L": 0.9, "K": 0.35, "M": 0.3}},
        {"id": "kingdom", "label_ko": "왕정", "vector_slkm": {"S": 0.87, "L": 0.97, "K": 0.35, "M": 0.8}},
        {"id": "exile", "label_ko": "포로", "vector_slkm": {"S": 0.45, "L": 0.65, "K": 0.8, "M": 0.4}},
        {"id": "restoration", "label_ko": "회복", "vector_slkm": {"S": 0.74, "L": 0.79, "K": 0.86, "M": 0.89}},
    ]
    if refit_json.is_file():
        refit = _load_json(refit_json)
        best = refit.get("best") or {}
        if isinstance(best.get("archetypes"), list) and best["archetypes"]:
            archetypes = best["archetypes"]

    return {
        "schema": "logos_fractal_archetype_4d_matrix_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "hypothesis_tag": "[HYPO]",
        "bootstrap_note": "auto-generated when base matrix missing; archetypes from refit best when available",
        "projection_lexicon": _default_lexicon(),
        "decision_thresholds": {
            "critical_resonance_cut": 0.9,
            "watch_resonance_cut": 0.8,
        },
        "decision_mapping": {
            "critical": "HOLD",
            "watch": "WATCH",
            "normal": "OBSERVE",
        },
        "archetypes": archetypes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Bootstrap fractal 4D archetype matrix JSON.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--refit-json", type=Path, default=DEFAULT_REFIT)
    ap.add_argument("--force", action="store_true", help="Overwrite even if output exists.")
    args = ap.parse_args()

    out_path = Path(args.output_json).resolve()
    if out_path.is_file() and not args.force:
        print(json.dumps({"ok": True, "skipped": True, "output_json": str(out_path)}, ensure_ascii=False))
        return 0

    doc = build_matrix(refit_json=Path(args.refit_json).resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(out_path).replace("\\", "/"),
                "archetype_count": len(doc.get("archetypes") or []),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
