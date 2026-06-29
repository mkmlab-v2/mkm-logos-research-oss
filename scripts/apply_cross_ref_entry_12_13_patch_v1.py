#!/usr/bin/env python3
"""Apply commander-approved CROSS_REF ENTRY_12/13 patch from diff preview (hg-05)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
PREVIEW = ROOT / "reports/cross_ref_entry_12_13_apply_diff_preview_v1_latest.json"
OUT_LOG = ROOT / "reports/cross_ref_entry_12_13_apply_log_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def apply(*, dry_run: bool, approver: str) -> dict[str, Any]:
    preview = _load(PREVIEW)
    draft = _load(DRAFT)
    patches = {e["entry_id"]: e["after"] for e in preview.get("entries") or []}
    applied: list[dict[str, Any]] = []
    entries = draft.get("entries") or []
    for i, row in enumerate(entries):
        eid = row.get("entry_id")
        if eid not in patches:
            continue
        after = patches[eid]
        before_snap = {k: row.get(k) for k in after}
        for k, v in after.items():
            if k == "entry_id":
                continue
            row[k] = v
        entries[i] = row
        applied.append({"entry_id": eid, "fields": list(after.keys()), "before": before_snap})

    log = {
        "schema": "cross_ref_entry_12_13_apply_log_v1",
        "generated_at_utc": _utc(),
        "dry_run": dry_run,
        "approver": approver,
        "preview_ref": str(PREVIEW.relative_to(ROOT)),
        "draft_path": str(DRAFT.relative_to(ROOT)),
        "applied": applied,
        "verified_anchor_claimed": False,
        "reproduce": "py scripts/apply_cross_ref_entry_12_13_patch_v1.py --apply --approver commander",
    }

    if not dry_run:
        backup = DRAFT.with_suffix(".json.bak_entry_12_13_apply")
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
    ap.add_argument("--approver", default="commander")
    args = ap.parse_args()
    if not args.dry_run and not args.apply:
        print(json.dumps({"ok": False, "reason": "pass --dry-run or --apply"}, ensure_ascii=False))
        return 1
    if not PREVIEW.is_file():
        print(json.dumps({"ok": False, "reason": "diff_preview_missing"}, ensure_ascii=False))
        return 1
    log = apply(dry_run=args.dry_run, approver=args.approver)
    print(json.dumps({"ok": True, "dry_run": args.dry_run, "applied": len(log["applied"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
