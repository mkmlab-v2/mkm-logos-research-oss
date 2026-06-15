#!/usr/bin/env python3
"""Build coding deep pack no-match fallback spec (B-track PoC).

Documents semantic_v2_stub fallback when catalog lane is active but snippet does not match.
research_only · SEND_GATE HOLD · no ACTIVE mutation.
"""

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

DEFAULT_GATE = ROOT / "docs/final/artifacts/compression_coding_deep_pack_gate_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_coding_deep_pack_fallback_spec_v1_latest.json"


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
    ext = gate.get("extension_cases") or []
    return {
        "schema": "compression_coding_deep_pack_fallback_spec_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "gate_artifact": _rel(gate_path),
        "lane_active_when": [
            "enable_coding_deep_pack=true",
            "sku_class=mask AND routed shard_id=zone_f_code",
        ],
        "match_order": [
            "exact_snippet",
            "literal_slot_identifier_rename",
        ],
        "on_catalog_match": {
            "roundtrip_path": "template_catalog_wire_v1",
            "wire_prefix": "[ZF_MASK:",
            "integrity_flag": "coding_deep_pack_wire_v1",
        },
        "on_no_match": {
            "fallback_path": "semantic_v2_stub",
            "integrity_flags": {
                "no_match": "coding_deep_pack_no_catalog_match",
                "fallback_path": "coding_deep_pack_fallback_path",
            },
            "exact_restore_ok": False,
            "metrics_axis": "semantic_v2_stub_separate_from_template_wire",
            "note_ko": "카탈로그 미매칭 시 ZF_MASK wire를 쓰지 않고 기존 v2 semantic stub으로 degrade. saving/Jaccard는 별도 축.",
        },
        "template_catalog_row_count": int(catalog.get("row_count") or 0),
        "extension_case_count": len(ext),
        "forbidden": [
            "claim_template_wire_saving_for_unmatched_snippet",
            "merge_semantic_fallback_into_coding_pack_headline",
        ],
        "reproduce": [
            "py scripts/build_compression_coding_deep_pack_gate_v1.py",
            "py scripts/build_compression_coding_deep_pack_fallback_spec_v1.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build coding deep pack fallback spec")
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
