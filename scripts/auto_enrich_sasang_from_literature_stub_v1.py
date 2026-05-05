#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto-fill ``sasang_constitution`` on joint stub rows using title + catalog abstract (regex/heuristic).

- **Never** sets ``birth_resolution`` (no automated DOB inference).
- If multiple distinct Sasang types appear in the blob, sets extraction state ``ambiguous`` and leaves
  ``sasang_constitution`` null.
- Writes new JSONL; does not overwrite curator-only ``sasang_saju_joint_benchmark_v1.jsonl`` by default.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUBS = ROOT / "data" / "myeongni" / "sasang_saju_joint_stub_rows_from_catalog_v1.jsonl"
DEFAULT_CATALOG = ROOT / "data" / "myeongni" / "sasang_saju_literature_catalog_strict_high_signal_v1.jsonl"
DEFAULT_OUT = ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_auto_v1.jsonl"

# (regex, label_en, label_ko) — checked in order; collect all non-overlapping best left-to-right
TYPE_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"태음인|Tae[-\s]?Eum(?:\s+type|\s+Sasang|\s+types)?", re.I), "Tae-Eum", "태음인"),
    (re.compile(r"소양인|So[-\s]?Yang(?:\s+type|\s+Sasang)?", re.I), "So-Yang", "소양인"),
    (re.compile(r"소음인|So[-\s]?Eum(?:\s+type|\s+Sasang)?", re.I), "So-Eum", "소음인"),
    (re.compile(r"태양인|Tae[-\s]?Yang(?:\s+type|\s+Sasang)?", re.I), "Tae-Yang", "태양인"),
)


def _load_catalog_by_pmid(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if str(row.get("schema") or "") != "sasang_saju_literature_catalog_row_v1":
            continue
        pmid = str(row.get("pmid") or "").strip()
        if pmid:
            out[pmid] = row
    return out


def _blob_for_stub(stub: dict[str, Any], cat: dict[str, dict[str, Any]]) -> str:
    pmids = stub.get("literature_catalog_pmids") or []
    pmid = str(pmids[0] if pmids else "").strip()
    parts: list[str] = []
    snap = stub.get("literature_catalog_snapshot") or {}
    parts.append(str(snap.get("title") or ""))
    if pmid and pmid in cat:
        parts.append(str(cat[pmid].get("abstractText") or ""))
    return "\n".join(parts)


def _find_type_hits(blob: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for rx, en, ko in TYPE_RULES:
        for m in rx.finditer(blob):
            hits.append(
                {
                    "label_en": en,
                    "label_ko": ko,
                    "span": m.group(0),
                    "start": m.start(),
                    "end": m.end(),
                }
            )
    hits.sort(key=lambda h: h["start"])
    return hits


def _unique_labels(hits: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {(h["label_en"], h["label_ko"]) for h in hits}


def _quote_window(blob: str, start: int, end: int, *, width: int = 90) -> str:
    lo = max(0, start - width // 2)
    hi = min(len(blob), end + width // 2)
    return blob[lo:hi].replace("\n", " ").strip()


def enrich_stub(stub: dict[str, Any], cat: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out = dict(stub)
    pmids = out.get("literature_catalog_pmids") or []
    pmid = str(pmids[0] if pmids else "").strip()
    blob = _blob_for_stub(stub, cat)
    hits = _find_type_hits(blob)
    uniq = _unique_labels(hits)

    extract: dict[str, Any] = {
        "schema": "literature_sasang_extract_v1",
        "hit_count": len(hits),
        "distinct_types": len(uniq),
    }

    if len(uniq) == 1 and hits:
        en, ko = next(iter(uniq))
        h0 = hits[0]
        quote = _quote_window(blob, h0["start"], h0["end"])
        out["sasang_constitution"] = {
            "label_en": en,
            "label_ko": ko,
            "confidence": 0.55,
            "source": {
                "pmid": pmid,
                "quote": quote,
                "method": "regex_title_abstract_v1",
            },
        }
        out["benchmark_tier"] = "auto_literature_sasang_only"
        extract["state"] = "single_type"
    elif len(uniq) > 1:
        out["sasang_constitution"] = None
        out["benchmark_tier"] = "pending_human_merge"
        extract["state"] = "ambiguous_multi_type"
        extract["labels_seen"] = [{"label_en": a, "label_ko": b} for a, b in sorted(uniq)]
    else:
        out["sasang_constitution"] = None
        out["benchmark_tier"] = "pending_human_merge"
        extract["state"] = "no_match"

    out["literature_sasang_extract"] = extract
    out["provenance"] = (
        str(out.get("provenance") or "")
        + " | auto_enrich_sasang_from_literature_stub_v1.py (birth_resolution intentionally unset)."
    ).strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stubs", type=Path, default=DEFAULT_STUBS)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.stubs.is_file():
        print(f"Missing stubs: {args.stubs}", file=sys.stderr)
        return 2

    cat = _load_catalog_by_pmid(args.catalog)
    rows_out: list[dict[str, Any]] = []
    stats = {"rows": 0, "single_type": 0, "ambiguous": 0, "no_match": 0}

    for line in args.stubs.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        stub = json.loads(line)
        if str(stub.get("schema") or "") != "sasang_saju_joint_benchmark_row_v1":
            continue
        enriched = enrich_stub(stub, cat)
        rows_out.append(enriched)
        stats["rows"] += 1
        st = (enriched.get("literature_sasang_extract") or {}).get("state")
        if st == "single_type":
            stats["single_type"] += 1
        elif st == "ambiguous_multi_type":
            stats["ambiguous"] += 1
        else:
            stats["no_match"] += 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in rows_out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary_path = args.out.with_name(args.out.stem + "_summary_v1.json")
    summary_path.write_text(
        json.dumps({"schema": "sasang_saju_joint_auto_enrich_summary_v1", "stats": stats}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(args.out), "summary": str(summary_path), "stats": stats}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
