#!/usr/bin/env python3
"""Build ko premium cs deep pack no-match fallback spec (B-track PoC)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_GATE = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_gate_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_fallback_spec_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_fallback_spec(*, gate_path: Path) -> dict[str, Any]:
    gate = _load(gate_path)
    catalog = gate.get("template_catalog") or {}
    return {
        "schema": "compression_ko_premium_cs_deep_pack_fallback_spec_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "gate_artifact": _rel(gate_path),
        "vertical_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "lane_active_when": [
            "enable_ko_premium_cs_deep_pack=true",
            "sku_class=mask AND routed shard_id=zone_ko_premium_cs_v1",
        ],
        "match_order": ["exact_snippet"],
        "on_catalog_match": {
            "roundtrip_path": "template_catalog_wire_v1",
            "wire_prefix": "[CS_MASK:",
            "integrity_flag": "ko_premium_cs_deep_pack_wire_v1",
        },
        "on_no_match": {
            "fallback_path": "semantic_v2_stub",
            "integrity_flags": {
                "no_match": "ko_premium_cs_deep_pack_no_catalog_match",
                "fallback_path": "ko_premium_cs_deep_pack_fallback_path",
            },
            "exact_restore_ok": False,
            "metrics_axis": "semantic_v2_stub_separate_from_cs_mask_wire",
        },
        "template_catalog_row_count": int(catalog.get("row_count") or 0),
        "forbidden": [
            "merge_with_en_business_headline",
            "merge_with_coding_deep_pack_headline",
            "claim_cs_mask_saving_for_unmatched_snippet",
            "collapse_wtt_shortcap_with_cs_mask_wire",
        ],
        "reproduce": [
            "py scripts/build_compression_ko_premium_cs_deep_pack_gate_v1.py",
            "py scripts/build_compression_ko_premium_cs_deep_pack_fallback_spec_v1.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build ko premium cs deep pack fallback spec")
    ap.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.gate.is_file():
        print(f"MISSING gate: {args.gate}", file=sys.stderr)
        return 1
    doc = build_fallback_spec(gate_path=args.gate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
