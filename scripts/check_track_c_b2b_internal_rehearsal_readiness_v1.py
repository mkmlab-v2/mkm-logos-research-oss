#!/usr/bin/env python3
"""15-min internal B2B rehearsal pre-flight checklist (Track C, no auto-send)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/track_c_b2b_internal_rehearsal_readiness_v1_latest.json"

REQUIRED: tuple[tuple[str, str], ...] = (
    ("meeting_pack_index", "docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md"),
    ("rehearsal_runbook", "docs/final/artifacts/track_c_b2b_internal_rehearsal_runbook_v1_latest.md"),
    ("two_layer_print_html", "docs/final/artifacts/track_c_b2b_two_layer_agent_slide_v1_print.html"),
    ("meeting_pack_readiness", "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"),
    ("counsel_copy_scan", "reports/track_c_b2b_counsel_copy_scan_v1_latest.json"),
    ("showroom_smoke", "reports/showroom_trust_viz_public_chain_smoke_latest.json"),
    ("deck_screenshots_manifest", "reports/track_c_showroom_deck_screenshots_manifest_v1_latest.json"),
    ("counsel_zip", "docs/final/artifacts/track_c_b2b_counsel_export_pack_v1.zip"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    checks: list[dict[str, Any]] = []
    blocking: list[str] = []

    for cid, rel in REQUIRED:
        path = ROOT / rel
        ok = path.is_file()
        row: dict[str, Any] = {"id": cid, "path": rel, "ok": ok}
        checks.append(row)
        if not ok:
            blocking.append(rel)
            continue

        if cid == "meeting_pack_readiness":
            doc = _read_json(path) or {}
            row["ready_for_internal_meeting"] = doc.get("ready_for_internal_meeting")
            row["ready_for_external_send"] = doc.get("ready_for_external_send")
            if not doc.get("ready_for_internal_meeting"):
                blocking.append(f"{rel}:ready_for_internal_meeting=false")
        elif cid == "counsel_copy_scan":
            doc = _read_json(path) or {}
            row["scan_ok"] = doc.get("scan_ok")
            if not doc.get("scan_ok"):
                blocking.append(f"{rel}:scan_ok=false")
        elif cid == "showroom_smoke":
            doc = _read_json(path) or {}
            row["smoke_ok"] = doc.get("ok")
            if not doc.get("ok"):
                blocking.append(f"{rel}:ok=false")
        elif cid == "deck_screenshots_manifest":
            doc = _read_json(path) or {}
            row["screenshots_ok"] = doc.get("ok")
            captured = doc.get("captured") or []
            row["screenshot_count"] = len(captured) if isinstance(captured, list) else 0
            if not doc.get("ok"):
                blocking.append(f"{rel}:ok=false")

    payload = {
        "schema": "track_c_b2b_internal_rehearsal_readiness_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "lane": "track_c_b2b",
        "ready_for_15min_rehearsal": len(blocking) == 0,
        "ready_for_external_send": False,
        "blocking": blocking,
        "checks": checks,
        "runbook_ref": "docs/final/artifacts/track_c_b2b_internal_rehearsal_runbook_v1_latest.md",
        "boundary_ack": "Rehearsal readiness is ops pre-flight only; not legal sign-off or customer production GO.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": payload["ready_for_15min_rehearsal"],
                "blocking_count": len(blocking),
                "output": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0 if payload["ready_for_15min_rehearsal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
