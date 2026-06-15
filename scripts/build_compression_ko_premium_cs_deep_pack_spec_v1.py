#!/usr/bin/env python3
"""Build Korean premium CS deep pack vertical pin spec (B-track)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_spec_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def build_spec() -> dict[str, Any]:
    return {
        "schema": "compression_ko_premium_cs_deep_pack_spec_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "track_a_active_untouched": True,
        "vertical_id": "zone_ko_premium_cs_v1",
        "vertical_label": "ko_premium_cs_turn",
        "language": "ko",
        "sku_class": "mask",
        "corpus_tag_binding": "wtt-premium-cs-customer-v1",
        "three_layer_layout": {
            "core": {"role": "master lexicon lookup (41k+)", "note": "Shared compression core."},
            "router": {
                "shard_policy": _rel(ROOT / "codebook/shards/zone_ko_premium_cs_v1.json"),
                "forced_shard_id": "zone_ko_premium_cs_v1",
                "hybrid_shortcap_note": "corpus_tag shortcap axis is separate from CS_MASK deep pack wire",
            },
            "deep_pack": {
                "wire_prefix": "CS_MASK",
                "wire_schema": "compression_ko_premium_cs_deep_pack_wire_v1",
                "template_catalog_production": _rel(
                    ROOT / "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl"
                ),
                "template_manifest": _rel(ROOT / "codebook/templates/zone_ko_premium_cs_templates_manifest_v1.json"),
                "twin_gate_artifact": _rel(
                    ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_gate_v1_latest.json"
                ),
                "fallback_spec": _rel(
                    ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_fallback_spec_v1_latest.json"
                ),
                "codec_lib": "scripts/compression_ko_premium_cs_deep_pack_v1_lib.py",
                "extract_lib": "scripts/extract_zone_ko_premium_cs_template_seeds_v1_lib.py",
                "gate_builder": "scripts/build_compression_ko_premium_cs_deep_pack_gate_v1.py",
            },
        },
        "mask_preservation": {
            "required_tokens": ["███", "****"],
            "exact_restore_includes_masks": True,
        },
        "axis_separation": {
            "not_merged_with": [
                "zone_h_en_business_v1 BIZ_MASK",
                "zone_f_code ZF_MASK",
                "wtt-premium-cs-customer-v1 shortcap headline only",
            ],
            "fail_comp_guard": "FAIL-COMP-004",
        },
        "reproduce": [
            "py scripts/build_compression_ko_premium_cs_deep_pack_spec_v1.py",
            "py scripts/build_compression_ko_premium_cs_deep_pack_gate_v1.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build ko premium cs deep pack spec")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_spec()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
