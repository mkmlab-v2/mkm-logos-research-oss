#!/usr/bin/env python3
"""Build Oracle Logos Tier-2 Cursor inject manifest (post-unlock SSOT).

Extends Tier-1 12-pin firewall with Tier-2 protocol pointers; Tier-3 still blocked.

  py scripts/build_logos_oracle_tier2_cursor_inject_manifest_v1.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TIER1_MANIFEST = ROOT / "reports/logos_oracle_tier1_cursor_inject_manifest_v1_latest.json"
OUT = ROOT / "reports/logos_oracle_tier2_cursor_inject_manifest_v1_latest.json"
READINESS = ROOT / "docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json"
TIER2_PROTOCOL = ROOT / "docs/final/artifacts/logos_oracle_tier2_incremental_append_protocol_v1_latest.json"
TIER3_PROTOCOL = ROOT / "docs/final/artifacts/logos_oracle_tier3_narrative_upgrade_protocol_v1_latest.json"
SIDECAR = ROOT / "storage/meta/mkm_sidecar_constitution_paths_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_manifest(root: Path) -> dict[str, Any]:
    if not TIER1_MANIFEST.is_file():
        raise FileNotFoundError(f"missing tier1 manifest: {TIER1_MANIFEST}")
    base = _read(TIER1_MANIFEST)
    readiness = _read(READINESS) if READINESS.is_file() else {}
    tier2 = _read(TIER2_PROTOCOL) if TIER2_PROTOCOL.is_file() else {}
    tier3 = _read(TIER3_PROTOCOL) if TIER3_PROTOCOL.is_file() else {}
    sidecar = _read(SIDECAR) if SIDECAR.is_file() else {}
    logos_seg = (sidecar.get("segments") or {}).get("logos_ops_memory_cursor_inject") or {}

    send_gate = str(readiness.get("send_gate") or tier2.get("send_gate") or "HOLD").upper()
    tier2_ready = bool(readiness.get("tier2_cursor_rules_full_upgrade_ready"))
    tier3_ready = bool(readiness.get("tier3_constitution_narrative_full_upgrade_ready"))

    tier2_inject_pins = [
        {
            "pin_id": "constitution_sidecar_logos_ops_memory",
            "slice_kind": "constitution_sidecar_segment",
            "file_path": str(SIDECAR.relative_to(root)).replace("\\", "/"),
            "segment_id": "logos_ops_memory_cursor_inject",
            "essence": logos_seg.get("essence"),
            "must_keep_tags": logos_seg.get("must_keep_tags") or [],
            "tier2_only": True,
        },
        {
            "pin_id": "tier2_incremental_append_protocol",
            "slice_kind": "json_summary",
            "file_path": str(TIER2_PROTOCOL.relative_to(root)).replace("\\", "/"),
            "json_pointers": ["/blocker_release_matrix", "/incremental_append_steps"],
            "essence": "Tier-2 incremental append gate — sidecar slices only; no CONSTITUTION full rewrite",
            "must_keep_tags": ["incremental_append", "FAIL-COMP-004", "research_only"],
            "tier2_only": True,
        },
        {
            "pin_id": "a2a_tier3_oracle_wire_handoff_brief",
            "slice_kind": "markdown_pointer",
            "file_path": "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_oracle_v1_latest.md",
            "essence": "A2A Tier-3 parallel oracle chat brief — peer paste; NOT MISSION_LOG full",
            "must_keep_tags": ["SEND_GATE", "parallel chat", "HYPO"],
            "tier3_prep_only": True,
        },
    ]

    still_blocked = [
        "Phase3 covenant queue bulk inject",
        "Phase4 apocrypha sidecar canonical merge",
        "Phase5 offline_4d maintenance deferred edges",
        "resonance_cap bump / bloom deepen",
        "Track A promotion / live trading auto-merge",
    ]
    if not tier3_ready:
        still_blocked.append("Tier-3 CONSTITUTION narrative full upgrade (commander+legal pending)")

    return {
        "schema": "logos_oracle_tier2_cursor_inject_manifest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": send_gate,
        "hypothesis_class": "HYPO",
        "inject_entrypoint": base.get("inject_entrypoint"),
        "tier1_gate": {
            **(base.get("tier1_gate") or {}),
            "tier2_cursor_rules_full_upgrade_ready": tier2_ready,
            "tier3_constitution_narrative_full_upgrade_ready": tier3_ready,
            "checks_pass": readiness.get("checks_pass_count"),
        },
        "tier2_gate": {
            "artifact": str(TIER2_PROTOCOL.relative_to(root)).replace("\\", "/"),
            "tier2_cursor_rules_full_upgrade_ready": tier2_ready,
            "blockers_released": sum(
                1 for b in (tier2.get("blocker_release_matrix") or []) if b.get("released")
            ),
            "repro": "py scripts/run_logos_oracle_tier2_incremental_append_protocol_chain_v1.py --require-tier2-unlock",
        },
        "tier3_gate": {
            "artifact": str(TIER3_PROTOCOL.relative_to(root)).replace("\\", "/"),
            "tier3_constitution_narrative_full_upgrade_ready": tier3_ready,
            "blockers_released": sum(
                1 for b in (tier3.get("blocker_release_matrix") or []) if b.get("released")
            ),
            "repro": "py scripts/run_logos_oracle_tier3_narrative_upgrade_protocol_chain_v1.py",
        },
        "oracle_lane_pack_pins": base.get("oracle_lane_pack_pins") or [],
        "tier2_inject_pins": tier2_inject_pins,
        "explicitly_not_injected": still_blocked,
        "boundary_ack": (
            "Tier-2+3 unlocked = sidecar logos segment + Tier-2/3 protocol + A2A oracle brief injectable. "
            "Canonical merge / cap bump / offline_4d bulk remain forbidden."
            if tier3_ready
            else (
                "Tier-2 unlocked = constitution sidecar logos segment + protocol pointers injectable. "
                "Tier-3 narrative full upgrade remains blocked until separate commander+legal gates."
            )
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()
    try:
        doc = build_manifest(ROOT)
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.stdout_only:
        print(text)
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(
        f"send_gate={doc['send_gate']} tier2_ready={doc['tier2_gate']['tier2_cursor_rules_full_upgrade_ready']} "
        f"tier3_ready={doc['tier3_gate']['tier3_constitution_narrative_full_upgrade_ready']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
