#!/usr/bin/env python3
"""Apply artifact_path + P10 rail note to CROSS_REF ENTRY_01–11,14–16 (no satellite mutation)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
REGISTRY = ROOT / "docs/final/artifacts/cross_ref_dss_entry_rail_registry_v1_latest.json"
OUT_LOG = ROOT / "reports/cross_ref_dss_entry_rail_artifact_apply_log_v1_latest.json"

SKIP = {"ENTRY_12", "ENTRY_13"}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def apply(*, dry_run: bool) -> dict[str, Any]:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    draft = json.loads(DRAFT.read_text(encoding="utf-8-sig"))
    by_id = {p["entry_id"]: p for p in reg.get("packets") or []}
    applied: list[dict[str, Any]] = []
    for i, row in enumerate(draft.get("entries") or []):
        eid = row.get("entry_id")
        if eid not in by_id or eid in SKIP:
            continue
        pkt = by_id[eid]
        dss_doc = pkt.get("dss_doc")
        if not dss_doc:
            continue
        artifact = (
            str(dss_doc)
            if str(dss_doc).startswith("docs/")
            else f"reports/cross_ref_dss_entry_{str(eid).lower()}_rail_packet_v1_latest.json"
        )
        before = row.get("artifact_path")
        if before == artifact:
            continue
        if not dry_run:
            row["artifact_path"] = artifact
            note = str(row.get("note") or "")
            stamp = "P10 sequential rail packet linked."
            if stamp not in note:
                row["note"] = (note + " " + stamp).strip() if note else stamp
            draft["entries"][i] = row
        applied.append({"entry_id": eid, "artifact_path": artifact, "before": before})
    log = {
        "schema": "cross_ref_dss_entry_rail_artifact_apply_log_v1",
        "generated_at_utc": _utc(),
        "dry_run": dry_run,
        "applied": applied,
    }
    if not dry_run and applied:
        backup = DRAFT.with_suffix(".json.bak_p10_artifact_paths")
        shutil.copy2(DRAFT, backup)
        DRAFT.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log["backup_path"] = str(backup.relative_to(ROOT))
    OUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    OUT_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not args.dry_run and not args.apply:
        return 1
    log = apply(dry_run=args.dry_run)
    print(json.dumps({"ok": True, "applied": len(log["applied"]), "dry_run": args.dry_run}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
