#!/usr/bin/env python3
"""Bootstrap B-track apocrypha manuscript JSONL for null-corpus / satellite lane (no canon merge)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "data/logos/manuscripts/apocrypha_original_only_latest.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_apocrypha_bootstrap_manifest_v1_latest.json"

# Minimal B-track fixture — `[HYPO]` satellite seed only; not canon SSOT.
FIXTURE_ROWS: list[dict[str, Any]] = [
    {
        "verse_id": "apo:Tob.1.1",
        "original_text": "βίβλος λόγων Τωβιτ τοῦ Νεφθαλί",
        "source_ref": "btrack_fixture_lxx_greek_v1",
        "language": "grc",
    },
    {
        "verse_id": "apo:Tob.1.2",
        "original_text": "ὃς ἐν αἰχμαλωσίᾳ ἐν τῇ Νινευῇ",
        "source_ref": "btrack_fixture_lxx_greek_v1",
        "language": "grc",
    },
    {
        "verse_id": "apo:Wis.1.1",
        "original_text": "Ἀγαπήσατε δικαιοσύνην οἱ κρίνοντες τὴν γῆν",
        "source_ref": "btrack_fixture_lxx_greek_v1",
        "language": "grc",
    },
    {
        "verse_id": "apo:Sir.1.1",
        "original_text": "Πᾶσα σοφία παρὰ κυρίου",
        "source_ref": "btrack_fixture_lxx_greek_v1",
        "language": "grc",
    },
    {
        "verse_id": "apo:1Ma.1.1",
        "original_text": "Καὶ ἐγένετο μετὰ τὸ ἀποθανεῖν Αλεξανδρον",
        "source_ref": "btrack_fixture_lxx_greek_v1",
        "language": "grc",
    },
    {
        "verse_id": "apo:Jdt.1.1",
        "original_text": "Ἐν ἔτει δωδεκάτῳ τῆς βασιλείας Ναβουχοδονοσορ",
        "source_ref": "btrack_fixture_lxx_greek_v1",
        "language": "grc",
    },
    {
        "verse_id": "apo:Bar.1.1",
        "original_text": "Καὶ ἐγένετο λόγος τοῦ κυρίου πρὸς Βαρούχ",
        "source_ref": "btrack_fixture_lxx_greek_v1",
        "language": "grc",
    },
    {
        "verse_id": "apo:2Es.1.1",
        "original_text": "Καὶ ἐγένετο μετὰ τὰ ῥήματα ταῦτα",
        "source_ref": "btrack_fixture_lxx_greek_v1",
        "language": "grc",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_external(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not str(row.get("verse_id") or "").startswith("apo:"):
            vid = row.get("verse_id")
            if vid:
                row = dict(row)
                row["verse_id"] = f"apo:{vid}"
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--import-jsonl", type=Path, default=None, help="Optional external JSONL to merge after fixture")
    ap.add_argument("--force", action="store_true", help="Overwrite existing output")
    args = ap.parse_args()

    if args.output.is_file() and not args.force:
        print(f"exists (skip): {args.output} — use --force to overwrite")
        return 0

    rows = list(FIXTURE_ROWS)
    if args.import_jsonl and args.import_jsonl.is_file():
        rows.extend(_load_external(args.import_jsonl))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "schema": "logos_apocrypha_bootstrap_manifest_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "row_count": len(rows),
        "output_jsonl": str(args.output.relative_to(ROOT)).replace("\\", "/"),
        "fixture_only": args.import_jsonl is None,
        "track_wall": {
            "merge_into_canon_complete_jsonl": False,
            "ready_for_external_send": False,
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
