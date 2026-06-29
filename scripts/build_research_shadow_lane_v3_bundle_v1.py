#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge shadow lane v2 layers + comparative theology panorama -> showroom v3 JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_V2_ART = ROOT / "docs/final/artifacts/research_shadow_lane_v2_bundle_v1_latest.json"
DEFAULT_DIGEST = ROOT / "docs/final/artifacts/comparative_theology_panorama_digest_v1_latest.json"
DEFAULT_FOUR_SLOT = ROOT / "docs/final/artifacts/logos_four_slot_generation_envelope_v1_latest.json"
DEFAULT_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_research_shadow_lane_v3.json"
)
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/research_shadow_lane_v3_bundle_v1_latest.json"

SCHEMA_VERSION = "research_shadow_lane_v3_bundle_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build research shadow lane v3 bundle.")
    ap.add_argument("--v2-artifact", type=Path, default=DEFAULT_V2_ART)
    ap.add_argument("--digest-json", type=Path, default=DEFAULT_DIGEST)
    ap.add_argument("--four-slot-json", type=Path, default=DEFAULT_FOUR_SLOT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    args = ap.parse_args()

    def _p(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    v2 = _load(_p(args.v2_artifact))
    digest = _load(_p(args.digest_json))
    four_slot = _load(_p(args.four_slot_json)) if _p(args.four_slot_json).is_file() else {}

    layers = dict(v2.get("layers") or {})
    layers["comparative_theology"] = digest
    if four_slot:
        layers["four_slot_contract"] = four_slot

    entries = digest.get("panorama_entries") or []
    primary_ref = digest.get("primary_anchor_ref")
    primary = next((e for e in entries if e.get("anchor_ref") == primary_ref), entries[0] if entries else {})

    doc = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "issue_id": v2.get("issue_id") or digest.get("issue_id"),
        "query_ko": v2.get("query_ko"),
        "disclaimer": {
            "evidence_tier": "hypo_research_only",
            "gating_status": "NON_GATING",
            "note_ko": (
                "Shadow Lane v3: v2(경계·상징·상상력) + 학파 파노라마 digest + 4슬롯 생성 계약. "
                "학파 reading 전부 imagination_path/unknown_gap. 환각 제거 주장 없음."
            ),
        },
        "rail_status": v2.get("rail_status"),
        "layers": layers,
        "high_dim_hypotheses": v2.get("high_dim_hypotheses") or [],
        "comparative_panorama_summary": {
            "primary_anchor_ref": primary_ref,
            "entry_count": digest.get("entry_count") or len(entries),
            "anchors": [e.get("anchor_ref") for e in entries],
            "school_count_primary": len(primary.get("school_lanes") or []),
            "enforcement_status": (primary.get("imagination_budget_enforcement") or {}).get("status"),
        },
        "reproduce": {
            "chain": "powershell -File scripts/run_research_shadow_lane_v3_chain_v1.ps1",
        },
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    out_json = _p(args.out_json)
    out_art = _p(args.out_artifact)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_art.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(payload, encoding="utf-8")
    out_art.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
