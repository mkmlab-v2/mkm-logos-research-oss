#!/usr/bin/env python3
"""[HYPO] Build ng40 salience hook JSON from archetype nav frame (no codec wiring)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
NAV_DEFAULT = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
)
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_salience_hook_only.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def build_hook(nav: dict[str, Any], *, wired: bool) -> dict[str, Any]:
    anchors = list(nav.get("modern_concept_anchors") or [])
    weights: dict[str, float] = {}
    bridges: list[dict[str, Any]] = []
    for a in anchors:
        cid = str(a.get("concept_id", ""))
        w = float(a.get("salience_weight_stub", 0.0))
        if cid:
            weights[cid] = w
        art = a.get("bridge_artifact")
        bridges.append(
            {
                "concept_id": cid,
                "bridge_artifact": art,
                "present": bool(art and (ROOT / str(art)).is_file()),
                "human_reviewed_bridge": bool(a.get("human_reviewed_bridge")),
            }
        )
    contract = nav.get("salience_contract") or {}
    return {
        "schema": "ng40_salience_hook_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "wired_into_ng40_codec": wired,
        "prior_source": _rel(NAV_DEFAULT),
        "navigation_graph_edge_count": len(
            (nav.get("navigation_graph") or {}).get("edges") or []
        ),
        "concept_salience_weights": weights,
        "concept_bridge_bindings": bridges,
        "mask_application": "latent_salience_keep_ratio_modifier_only",
        "decode_contract": contract.get("decode_contract")
        or "recon = verbatim_spine_decode(pkt) only",
        "forbidden": list(contract.get("forbidden") or []),
        "default_keep_ratio_stub": 0.82,
        "operator_note_ko": "Phase 1: JSON hook only; run_nextgen_verbatim_spine_bench hybrid mode consumes keep_ratio separately",
        "lut_status": (nav.get("lut") or {}).get("status", "TBD"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nav-json", type=Path, default=NAV_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--mark-wired",
        action="store_true",
        help="Set wired_into_ng40_codec true (default false for phase 1)",
    )
    args = ap.parse_args()
    if not args.nav_json.is_file():
        print(json.dumps({"error": "missing_nav_frame", "path": str(args.nav_json)}))
        return 2
    nav = json.loads(args.nav_json.read_text(encoding="utf-8-sig"))
    out_doc = build_hook(nav, wired=bool(args.mark_wired))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "wired": out_doc["wired_into_ng40_codec"],
                "concepts": len(out_doc["concept_salience_weights"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
