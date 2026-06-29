#!/usr/bin/env python3
"""Assemble WTT human pilot pack: curated catalog + protocol + enrollment stub ([HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "docs/final/artifacts/warmth_content_dose_catalog_curated_v1.json"
DEFAULT_PROTOCOL = ROOT / "docs/final/artifacts/fixtures/warmth_trigger_pilot_protocol_v1.example.json"
DEFAULT_ENROLLMENT = ROOT / "docs/final/artifacts/fixtures/warmth_trigger_pilot_enrollment_template_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/warmth_trigger_pilot_pack_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _catalog_readiness(catalog: dict[str, Any]) -> dict[str, Any]:
    items = catalog.get("items") or []
    approved = sum(
        1 for it in items if (it.get("curator_review") or {}).get("status") == "approved"
    )
    pending = len(items) - approved
    return {
        "item_count": len(items),
        "approved_count": approved,
        "pending_count": pending,
        "min_items_met": len(items) >= 10,
        "all_approved": pending == 0 and len(items) >= 10,
    }


def build_enrollment_template(*, target_n: int, experiment_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(1, target_n + 1):
        rows.append(
            {
                "enrollment_id": f"{experiment_id}_slot_{i:03d}",
                "participant_status": "unassigned",
                "assigned_content_id": None,
                "session_id": None,
                "consent_ack": False,
                "pre": None,
                "post": None,
            }
        )
    return rows


def build_pack(
    *,
    catalog: dict[str, Any],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    cat_ready = _catalog_readiness(catalog)
    target_n = int(protocol.get("target_n_participants", 30))
    exp_id = protocol.get("provenance", {}).get("experiment_id", "wtt_epb_pilot_01")

    content_ids = [
        (it.get("dose_item") or {}).get("content_id")
        for it in (catalog.get("items") or [])
    ]

    return {
        "schema": "warmth_trigger_pilot_pack_v1",
        "generated_at_utc": _utc_now(),
        "track": "B",
        "research_only": True,
        "hypothesis_class": "HYPO",
        "disclaimer_ko": protocol.get("ethics", {}).get("disclaimer_ko"),
        "protocol_id": protocol.get("protocol_id"),
        "target_n_participants": target_n,
        "catalog_readiness": cat_ready,
        "pilot_ready_for_enrollment": cat_ready["all_approved"],
        "human_sessions_collected": 0,
        "human_n30_gate_met": False,
        "curated_content_ids": [c for c in content_ids if c],
        "protocol_ref": str(DEFAULT_PROTOCOL.relative_to(ROOT)).replace("\\", "/"),
        "catalog_ref": str(DEFAULT_CATALOG.relative_to(ROOT)).replace("\\", "/"),
        "enrollment_template_slots": target_n,
        "provenance": {
            "source": "build_warmth_trigger_pilot_pack_v1",
            "experiment_id": exp_id,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog-json", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--protocol-json", type=Path, default=DEFAULT_PROTOCOL)
    ap.add_argument("--write-enrollment-jsonl", type=Path, default=DEFAULT_ENROLLMENT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    catalog = _load_json(args.catalog_json)
    protocol = _load_json(args.protocol_json)
    pack = build_pack(catalog=catalog, protocol=protocol)

    target_n = int(protocol.get("target_n_participants", 30))
    exp_id = protocol.get("provenance", {}).get("experiment_id", "wtt_epb_pilot_01")
    enrollment_rows = build_enrollment_template(target_n=target_n, experiment_id=exp_id)

    args.write_enrollment_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.write_enrollment_jsonl.open("w", encoding="utf-8") as fh:
        for row in enrollment_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "pilot_ready_for_enrollment": pack["pilot_ready_for_enrollment"],
                "curated_items": pack["catalog_readiness"]["item_count"],
                "enrollment_slots": target_n,
                "out": str(args.out.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
