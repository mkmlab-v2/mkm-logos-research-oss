#!/usr/bin/env python3
"""Sync Trust Packet v2 layer pointers into commander_dev_day_pack [HYPO].

Reads lg_compression_trust_packet_onepager_outline_v1 + optional inter-agent status.
Does not claim Track A promotion from dev-coach context.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "reports" / "commander_dev_day_pack_latest.json"
OUTLINE = ROOT / "docs" / "final" / "artifacts" / "lg_compression_trust_packet_onepager_outline_v1.json"
INTER_AGENT_STATUS = ROOT / "docs" / "final" / "artifacts" / "mkm_inter_agent_encoding_status_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_trust_packet_v2(*, workspace: Path = ROOT) -> Dict[str, Any]:
    outline = _read_json(workspace / OUTLINE.relative_to(ROOT))
    inter = _read_json(workspace / INTER_AGENT_STATUS.relative_to(ROOT))
    layers = outline.get("three_layers") if isinstance(outline.get("three_layers"), dict) else {}

    layer_refs: Dict[str, Any] = {}
    for key in ("track_a_operational", "v2_trust_packet_draft", "l1_research_side_channel"):
        block = layers.get(key)
        if not isinstance(block, dict):
            continue
        layer_refs[key] = {
            "status": block.get("status"),
            "hypothesis_tier": block.get("hypothesis_tier", "B" if key != "track_a_operational" else None),
            "what_we_claim_count": len(block.get("what_we_claim") or []),
            "what_we_do_not_claim_count": len(block.get("what_we_do_not_claim") or []),
            "evidence_paths": (block.get("evidence_paths") or [])[:6],
            "dev_coach_use": "pointer_only_not_promotion_headline",
        }

    synced_from: List[str] = []
    if outline.get("schema"):
        synced_from.append(str(OUTLINE.relative_to(ROOT)).replace("\\", "/"))
    if inter.get("schema") or inter.get("generated_at_utc"):
        synced_from.append(str(INTER_AGENT_STATUS.relative_to(ROOT)).replace("\\", "/"))

    return {
        "hypothesis_labeled": True,
        "research_only": True,
        "non_gating": True,
        "synced_at_utc": _utc_now(),
        "synced_from": synced_from,
        "korean_title_ref": outline.get("korean_title"),
        "layers_ref": layer_refs,
        "inter_agent_encoding_status_ref": {
            "present": bool(inter),
            "schema": inter.get("schema"),
            "generated_at_utc": inter.get("generated_at_utc"),
        },
        "boundary_ko": "개발 코치·아침 TG는 Trust Packet 수치로 Track A·실매매 승격 단정 금지.",
    }


def merge_into_pack(pack: Dict[str, Any], trust: Dict[str, Any]) -> Dict[str, Any]:
    prior = pack.get("trust_packet_v2") if isinstance(pack.get("trust_packet_v2"), dict) else {}
    merged = {**prior, **trust}
    if prior.get("track_wall"):
        merged["track_wall"] = prior["track_wall"]
    pack["trust_packet_v2"] = merged
    pack["trust_packet_v2_sync"] = {
        "schema": "commander_dev_pack_trust_packet_v2_sync_v1",
        "merged_at_utc": _utc_now(),
    }
    return pack


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-json", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    pack_path = args.pack_json if args.pack_json.is_absolute() else ROOT / args.pack_json
    if not pack_path.is_file():
        print(f"MISSING: {pack_path} — run build_commander_dev_day_pack_v1.py first", flush=True)
        return 2

    pack = _read_json(pack_path)
    if pack.get("schema") != "commander_dev_day_pack_v1":
        print(f"BAD_SCHEMA: {pack.get('schema')}", flush=True)
        return 2

    trust = build_trust_packet_v2()
    pack = merge_into_pack(pack, trust)

    if not args.stdout_only:
        pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {pack_path}")
    print(json.dumps(pack.get("trust_packet_v2"), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
