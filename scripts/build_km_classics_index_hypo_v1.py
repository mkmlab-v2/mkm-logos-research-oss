#!/usr/bin/env python3
"""Korean medicine classics vendor inventory v1 [HYPO].

Stage A of korean_medicine_texts_clinician_rag_checklist — read-only file index.
Does not fetch network; scans --vendor-root on disk.
When catalog.json + texts/*/source.md exist, indexes canonical classics rows.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "km_classics_index_hypo_v1"
DEFAULT_OUT = ROOT / "reports/km_classics_index_hypo_v1_latest.json"
DEFAULT_MIRROR_REPORT = ROOT / "reports/km_classics_vendor_mirror_v1_latest.json"
TEXT_SUFFIXES = {".txt", ".md", ".json", ".xml", ".tei", ".csv"}


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _detect_encoding(sample: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
        try:
            sample.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "binary"


def _load_mirror_pin(mirror_report: Path | None) -> dict[str, Any] | None:
    if mirror_report is None or not mirror_report.is_file():
        return None
    try:
        doc = json.loads(mirror_report.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None
    if doc.get("schema") != "km_classics_vendor_mirror_v1":
        return None
    return {
        "commit_sha": doc.get("commit_sha"),
        "commit_sha_short": doc.get("commit_sha_short"),
        "upstream_url": doc.get("upstream_url"),
        "mirror_report": str(mirror_report.resolve()),
    }


def _catalog_rows(vendor_root: Path) -> list[dict[str, Any]] | None:
    catalog_path = vendor_root / "catalog.json"
    texts_dir = vendor_root / "texts"
    if not catalog_path.is_file() or not texts_dir.is_dir():
        return None

    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    rows = catalog.get("texts")
    if not isinstance(rows, list):
        return None

    entries: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        stable_id = str(row.get("id") or row.get("stable_id") or "").strip()
        if not stable_id:
            continue
        source_md = texts_dir / stable_id / "source.md"
        metadata_json = texts_dir / stable_id / "metadata.json"
        if not source_md.is_file():
            continue
        rel = source_md.relative_to(vendor_root).as_posix()
        size = source_md.stat().st_size
        head = source_md.read_bytes()[:4096]
        meta: dict[str, Any] = {}
        if metadata_json.is_file():
            try:
                meta = json.loads(metadata_json.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                meta = {}
        entries.append(
            {
                "source_id": stable_id,
                "work": str(row.get("title_ko") or row.get("title") or stable_id),
                "title_hanja": row.get("title_hanja"),
                "relative_path": rel,
                "suffix": ".md",
                "size_bytes": size,
                "encoding_guess": _detect_encoding(head),
                "quality_status": meta.get("quality_status"),
                "canonical": True,
            }
        )
    return entries


def inventory_vendor_root(
    vendor_root: Path,
    *,
    mirror_report: Path | None = DEFAULT_MIRROR_REPORT,
) -> dict[str, Any]:
    if not vendor_root.is_dir():
        raise FileNotFoundError(f"vendor_root_missing: {vendor_root}")

    catalog_entries = _catalog_rows(vendor_root)
    if catalog_entries is not None:
        entries = catalog_entries
        index_mode = "catalog_source_md"
    else:
        entries = []
        for path in sorted(vendor_root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            rel = path.relative_to(vendor_root).as_posix()
            size = path.stat().st_size
            head = path.read_bytes()[:4096]
            entries.append(
                {
                    "source_id": f"kmc-{_sha12(rel)}",
                    "work": path.stem,
                    "relative_path": rel,
                    "suffix": path.suffix.lower(),
                    "size_bytes": size,
                    "encoding_guess": _detect_encoding(head),
                    "canonical": False,
                }
            )
        index_mode = "recursive_text_scan"

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "version": 1,
        "hypothesis_tier": "B",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "vendor_root": str(vendor_root.resolve()),
        "index_mode": index_mode,
        "file_count": len(entries),
        "entries": entries,
        "clinician_lane_only": True,
        "personadiary_join": False,
    }
    pin = _load_mirror_pin(mirror_report)
    if pin:
        doc["vendor_pin"] = pin
    return doc


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--vendor-root",
        type=Path,
        default=ROOT / "tests/fixtures/km_classics_vendor_stub_hypo_v1",
        help="Local mirror of korean-medicine-texts (or stub)",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--mirror-report",
        type=Path,
        default=DEFAULT_MIRROR_REPORT,
        help="Optional mirror pin JSON (set empty path to skip)",
    )
    args = ap.parse_args()

    mirror_report = args.mirror_report
    if mirror_report is not None and str(mirror_report) == "":
        mirror_report = None

    try:
        doc = inventory_vendor_root(args.vendor_root, mirror_report=mirror_report)
    except FileNotFoundError as exc:
        print(str(exc), file=__import__("sys").stderr)
        return 1

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "index_mode": doc["index_mode"],
                "file_count": doc["file_count"],
                "out": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
