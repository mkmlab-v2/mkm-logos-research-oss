"""Classify zone_f_code template catalog rows: curated vs bulk_generated."""

from __future__ import annotations

import re
from typing import Any

BULK_SOURCE_RE = re.compile(r"^bulk-gen-", re.IGNORECASE)
PROVENANCE_CURATED = "curated"
PROVENANCE_BULK = "bulk_generated"


def infer_provenance(row: dict[str, Any]) -> str:
    explicit = str(row.get("catalog_provenance") or "").strip().lower()
    if explicit in (PROVENANCE_CURATED, PROVENANCE_BULK):
        return explicit
    source = str(row.get("source_row_id") or "")
    if BULK_SOURCE_RE.match(source):
        return PROVENANCE_BULK
    labels = row.get("labels")
    if isinstance(labels, list) and "bulk_generated" in labels:
        return PROVENANCE_BULK
    return PROVENANCE_CURATED


def annotate_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["catalog_provenance"] = infer_provenance(row)
    return out


def split_catalog_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    curated: list[dict[str, Any]] = []
    bulk: list[dict[str, Any]] = []
    for row in rows:
        if infer_provenance(row) == PROVENANCE_BULK:
            bulk.append(row)
        else:
            curated.append(row)
    total = len(rows)
    bulk_count = len(bulk)
    return {
        "total_row_count": total,
        "curated_row_count": len(curated),
        "bulk_row_count": bulk_count,
        "bulk_ratio": round(bulk_count / total, 6) if total else 0.0,
        "curated_ratio": round(len(curated) / total, 6) if total else 0.0,
        "curated_rows": curated,
        "bulk_rows": bulk,
    }
