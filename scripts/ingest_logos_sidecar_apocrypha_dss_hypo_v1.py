#!/usr/bin/env python3
"""Ingest Tier 2/3 apocrypha + DSS rows into HYPO sidecar JSONL.

Does NOT merge into logos_cosmic_anchor_batch_v1.

Reproducible:
  py scripts/ingest_logos_sidecar_apocrypha_dss_hypo_v1.py \\
    --input data/logos/sidecar_apocrypha_dss_hypo_v1.seed.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/logos_sidecar_apocrypha_dss_hypo_v1.schema.json"
SIDECAR = ROOT / "data/logos/sidecar_apocrypha_dss_hypo_v1.jsonl"
REPORT = ROOT / "docs/final/artifacts/logos_sidecar_apocrypha_dss_ingest_v1_latest.json"

REQUIRED = frozenset(
    {"tier", "hypothesis_class", "manuscript_id", "verse_ref", "text_original"}
)
TIER_VALUES = frozenset({"tier2_apocrypha", "tier3_dss"})


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def _validate_row(row: dict[str, Any], *, line_no: int) -> list[str]:
    errors: list[str] = []
    extra = set(row) - set(_load_schema().get("properties", {}))
    if extra:
        errors.append(f"line {line_no}: unknown keys {sorted(extra)}")
    missing = REQUIRED - set(row)
    if missing:
        errors.append(f"line {line_no}: missing {sorted(missing)}")
    if row.get("hypothesis_class") != "HYPO":
        errors.append(f"line {line_no}: hypothesis_class must be HYPO")
    if row.get("tier") not in TIER_VALUES:
        errors.append(f"line {line_no}: invalid tier")
    if row.get("non_gating") is not True:
        errors.append(f"line {line_no}: non_gating must be true")
    for key in ("manuscript_id", "verse_ref", "text_original"):
        if not str(row.get(key) or "").strip():
            errors.append(f"line {line_no}: {key} empty")
    return errors


def _row_key(row: dict[str, Any]) -> str:
    return f"{row['tier']}|{row['manuscript_id']}|{row['verse_ref']}"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def ingest(
    *,
    input_path: Path,
    sidecar_path: Path = SIDECAR,
    dry_run: bool = False,
) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    incoming = _read_jsonl(input_path)
    errors: list[str] = []
    for i, row in enumerate(incoming, start=1):
        errors.extend(_validate_row(row, line_no=i))
    if errors:
        raise SystemExit("\n".join(errors))

    existing: dict[str, dict[str, Any]] = {}
    if sidecar_path.is_file() and sidecar_path.stat().st_size > 0:
        for row in _read_jsonl(sidecar_path):
            existing[_row_key(row)] = row

    added = 0
    skipped = 0
    for row in incoming:
        key = _row_key(row)
        if key in existing:
            skipped += 1
            continue
        existing[key] = row
        added += 1

    if not dry_run:
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(existing[k], ensure_ascii=False) for k in sorted(existing)]
        sidecar_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    report = {
        "schema": "logos_sidecar_apocrypha_dss_ingest_v1",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "materialize_batch": False,
        "input_path": input_path.relative_to(ROOT).as_posix(),
        "sidecar_path": sidecar_path.relative_to(ROOT).as_posix(),
        "incoming_count": len(incoming),
        "added_count": added,
        "skipped_duplicate_count": skipped,
        "sidecar_total_count": len(existing),
        "reproducible_command": "py scripts/ingest_logos_sidecar_apocrypha_dss_hypo_v1.py",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, default=SIDECAR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    if not input_path.is_file():
        print(f"Missing input: {input_path}", file=sys.stderr)
        return 2
    report = ingest(input_path=input_path, sidecar_path=args.sidecar, dry_run=args.dry_run)
    print(f"WROTE: {REPORT if not args.dry_run else '(dry-run)'}")
    print(
        f"  added={report['added_count']} skipped_dup={report['skipped_duplicate_count']} "
        f"total={report['sidecar_total_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
