#!/usr/bin/env python3
"""Apply verified promotions to 11Q5 map + 4Q Ps.5 shadow map [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.shadow_lane_gematria_common_v1 import load_json

WITNESS_MAP_11Q5 = ROOT / "reports/dss_11q5_line_witness_map_v1_latest.json"
MAP_4Q = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
GATE = ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"
SCAN = ROOT / "reports/dss_line_witness_verification_scan_v1_latest.json"
OUT_11Q5 = WITNESS_MAP_11Q5
OUT_4Q = MAP_4Q


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _promotion_ids(gate: dict[str, Any], scan: dict[str, Any]) -> dict[str, set[str]]:
    by_entry: dict[str, set[str]] = {"ENTRY_12": set(), "ENTRY_13": set()}
    for row in gate.get("manual_promotions") or []:
        eid = str(row.get("entry_id") or "")
        wid = str(row.get("witness_id") or "")
        if eid in by_entry and wid:
            by_entry[eid].add(wid)
    for entry in scan.get("entries") or []:
        eid = str(entry.get("entry_id") or "")
        if eid not in by_entry:
            continue
        for row in entry.get("auto_verified") or []:
            wid = str(row.get("witness_id") or "")
            if wid:
                by_entry[eid].add(wid)
    return by_entry


def _mark_witness(witness: dict[str, Any], source: str) -> None:
    witness["mapping_status"] = "commander_verified_shadow_witness"
    witness["comparison_type"] = "commander_verified_shadow_witness"
    witness["promotion_source"] = source
    witness["promoted_at_utc"] = _utc()
    witness["writes_canon"] = False
    witness["non_gating"] = True


def _apply_entries_map(doc: dict[str, Any], promote_ids: dict[str, set[str]], source: str) -> int:
    promoted = 0
    for entry in doc.get("entries") or []:
        eid = str(entry.get("entry_id") or "")
        ids = promote_ids.get(eid) or set()
        for witness in entry.get("witnesses") or []:
            wid = str(witness.get("witness_id") or "")
            if wid in ids:
                _mark_witness(witness, source)
                promoted += 1
    if "summary" in doc:
        doc["summary"]["verified_line_witness_rows"] = sum(
            1
            for e in doc.get("entries") or []
            for w in e.get("witnesses") or []
            if str(w.get("mapping_status", "")).startswith("commander_verified")
        )
    return promoted


def _apply_flat_map(doc: dict[str, Any], ids: set[str], source: str) -> int:
    promoted = 0
    for witness in doc.get("witnesses") or []:
        wid = str(witness.get("witness_id") or "")
        if wid in ids:
            _mark_witness(witness, source)
            promoted += 1
    sm = doc.setdefault("summary", {})
    sm["commander_verified_shadow_rows"] = sum(
        1
        for w in doc.get("witnesses") or []
        if str(w.get("mapping_status", "")).startswith("commander_verified")
    )
    return promoted


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    gate = load_json(GATE)
    scan = load_json(SCAN)
    wmap_11 = load_json(WITNESS_MAP_11Q5)
    map_4q = load_json(MAP_4Q)
    if not map_4q and not wmap_11:
        print(json.dumps({"ok": False, "reason": "witness_maps_missing"}, ensure_ascii=False))
        return 1

    promote_ids = _promotion_ids(gate, scan)
    source = "p4_commander_manual_intake_v1"
    promoted_11 = 0
    promoted_4q = 0
    if wmap_11:
        updated_11 = json.loads(json.dumps(wmap_11))
        promoted_11 = _apply_entries_map(updated_11, promote_ids, source)
    else:
        updated_11 = wmap_11
    if map_4q:
        updated_4q = json.loads(json.dumps(map_4q))
        promoted_4q = _apply_flat_map(updated_4q, promote_ids.get("ENTRY_13") or set(), source)
    else:
        updated_4q = map_4q

    total = promoted_11 + promoted_4q
    if args.apply and total > 0:
        if promoted_11 > 0 and updated_11:
            OUT_11Q5.write_text(json.dumps(updated_11, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if promoted_4q > 0 and updated_4q:
            OUT_4Q.write_text(json.dumps(updated_4q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif args.apply and total == 0:
        print(json.dumps({"ok": True, "applied": False, "reason": "no_promotion_eligible"}, ensure_ascii=False))
        return 0

    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": not args.apply,
                "promotion_ids": {k: sorted(v) for k, v in promote_ids.items()},
                "promoted_11q5_rows": promoted_11,
                "promoted_4q_rows": promoted_4q,
                "would_promote_total": total,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
