#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promote rows from ``sasang_saju_joint_review_queue_v1.csv`` when curator filled birth + OK flag.

Requires columns: pmid, birth_instant_utc, iana_tz, is_male, curator_ok
Optional: sasang_label_ko, sasang_label_en, quote_from_paper, title (for display_name)

Appends ``sasang_saju_joint_benchmark_row_v1`` JSON lines to ``--target-jsonl`` (dedupe by person_id).
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "myeongni" / "sasang_saju_joint_review_queue_v1.csv"
DEFAULT_TARGET = ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_v1.jsonl"


def _truthy_curator_ok(val: str) -> bool:
    return str(val or "").strip().lower() in ("1", "y", "yes", "true", "ok", "approve")


def _parse_bool_male(val: str) -> bool | None:
    s = str(val or "").strip().lower()
    if s in ("", "-"):
        return None
    if s in ("1", "y", "yes", "true", "m", "male"):
        return True
    if s in ("0", "n", "no", "false", "f", "female"):
        return False
    return None


def _run_birth_cli(birth_instant_utc: str, iana_tz: str, is_male: bool) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_saju_global_birth_v1.py"),
        "--utc-instant",
        birth_instant_utc,
        "--iana-tz",
        iana_tz,
        "--compact",
    ]
    if is_male:
        cmd.append("--is-male")
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout or "run_saju_global_birth_v1 failed")
    line = (p.stdout or "").strip()
    if line.startswith("\ufeff"):
        line = line[1:]
    return json.loads(line)


def _existing_person_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        pid = str(r.get("person_id") or "").strip()
        if pid:
            out.add(pid)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--target-jsonl", type=Path, default=DEFAULT_TARGET)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.csv.is_file():
        print(f"Missing CSV: {args.csv}", file=sys.stderr)
        return 2

    existing = _existing_person_ids(args.target_jsonl)
    promoted: list[dict[str, Any]] = []
    errors: list[str] = []

    with args.csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            if not _truthy_curator_ok(row.get("curator_ok") or ""):
                continue
            pmid = str(row.get("pmid") or "").strip()
            birth = str(row.get("birth_instant_utc") or "").strip()
            tz = str(row.get("iana_tz") or "").strip()
            if not birth or not tz:
                errors.append(f"line {i}: missing birth_instant_utc or iana_tz")
                continue
            bm = _parse_bool_male(row.get("is_male") or "")
            if bm is None:
                errors.append(f"line {i}: is_male required (y/n) when curator_ok")
                continue
            person_id = f"curated_csv_pmid_{pmid}" if pmid else f"curated_csv_row_{i}"
            if person_id in existing:
                continue
            try:
                birth_doc = _run_birth_cli(birth, tz, bm)
            except Exception as e:
                errors.append(f"line {i} pmid={pmid}: {e}")
                continue

            saj = birth_doc.get("full_saju", {}).get("saju", {})
            pillars = {k: str(saj.get(k) or "") for k in ("year", "month", "day", "hour")} if isinstance(saj, dict) else {}

            sko = str(row.get("sasang_label_ko") or "").strip()
            sen = str(row.get("sasang_label_en") or "").strip()
            quote = str(row.get("quote_from_paper") or "").strip()
            sasang_const = None
            if sko or sen:
                sasang_const = {
                    "label_ko": sko or None,
                    "label_en": sen or None,
                    "confidence": 0.75,
                    "source": {
                        "pmid": pmid or None,
                        "quote": quote or None,
                        "method": "curator_csv_v1",
                    },
                }

            title = str(row.get("title") or "").strip()
            out_row: dict[str, Any] = {
                "schema": "sasang_saju_joint_benchmark_row_v1",
                "person_id": person_id,
                "display_name": title[:240] or person_id,
                "benchmark_tier": "curated_csv_with_saju_v1",
                "privacy_tier": "curator_attested_v1",
                "provenance": f"promote_joint_curated_csv_v1.py from {args.csv.name} row ~{i}",
                "sasang_constitution": sasang_const,
                "birth_resolution": {
                    "birth_instant_utc": birth,
                    "iana_tz": tz,
                    "is_male": bm,
                },
                "saju_engine_output_v1": {"pillars": pillars, "resolution": birth_doc.get("resolution")},
                "literature_catalog_pmids": [pmid] if pmid else [],
                "expectations": None,
            }
            promoted.append(out_row)
            existing.add(person_id)

    if args.dry_run:
        print(json.dumps({"dry_run": True, "would_append": len(promoted), "errors": errors}, ensure_ascii=False))
        return 1 if errors else 0

    args.target_jsonl.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.target_jsonl.is_file() else "w"
    with args.target_jsonl.open(mode, encoding="utf-8") as outf:
        for r in promoted:
            outf.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {"appended": len(promoted), "target": str(args.target_jsonl), "errors": errors},
            ensure_ascii=False,
        )
    )
    return 1 if errors and not promoted else 0


if __name__ == "__main__":
    raise SystemExit(main())
