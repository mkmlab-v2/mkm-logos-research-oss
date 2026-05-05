#!/usr/bin/env python3
"""Backfill corpus_profile_id for Global Atom academic onepagers."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGET_FILENAME = "global_atom_network_academic_onepager_latest.json"
TARGET_SCHEMA = "global_atom_network_academic_onepager_v1"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_profiles = root / "docs" / "final" / "artifacts" / "global_atom_corpus_profiles_v1.json"
    default_base_dir = root / "docs" / "final" / "artifacts"
    default_report = root / "docs" / "final" / "artifacts" / "global_atom_onepager_corpus_profile_backfill_latest.json"

    ap = argparse.ArgumentParser(description="Backfill corpus_profile_id in global atom onepager artifacts.")
    ap.add_argument("--base-dir", default=str(default_base_dir))
    ap.add_argument("--profiles-json", default=str(default_profiles))
    ap.add_argument("--write", action="store_true", help="Write updates to files.")
    ap.add_argument("--report-json", default=str(default_report))
    args = ap.parse_args()

    profiles_doc = _load_json(Path(args.profiles_json))
    default_profile = profiles_doc.get("default_profile_id")
    if not isinstance(default_profile, str) or not default_profile:
        raise SystemExit("invalid profiles file: default_profile_id missing")

    base_dir = Path(args.base_dir)
    if not base_dir.exists():
        raise SystemExit(f"missing base dir: {base_dir}")

    scanned = 0
    updated = 0
    already_ok = 0
    skipped = 0
    changes: list[dict[str, Any]] = []

    for path in base_dir.rglob(TARGET_FILENAME):
        scanned += 1
        doc = _load_json(path)
        if doc.get("schema") != TARGET_SCHEMA:
            skipped += 1
            continue
        current = doc.get("corpus_profile_id")
        if current == default_profile:
            already_ok += 1
            continue

        changes.append(
            {
                "path": str(path),
                "old_corpus_profile_id": current,
                "new_corpus_profile_id": default_profile,
            }
        )
        if args.write:
            doc["corpus_profile_id"] = default_profile
            _dump_json(path, doc)
            updated += 1

    report = {
        "schema": "global_atom_onepager_corpus_profile_backfill_v1",
        "generated_at_utc": _now_utc(),
        "base_dir": str(base_dir),
        "default_profile_id": default_profile,
        "write_mode": bool(args.write),
        "scanned_files": scanned,
        "already_ok": already_ok,
        "updated_files": updated,
        "pending_changes": len(changes) - updated if args.write else len(changes),
        "skipped_files": skipped,
        "changes": changes,
    }
    _dump_json(Path(args.report_json), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
