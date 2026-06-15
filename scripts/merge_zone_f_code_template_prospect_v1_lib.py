"""Plan and apply prospect → production zone_f_code template catalog merge."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.compression_coding_deep_pack_v1_lib import load_template_catalog
from scripts.extract_zone_f_code_template_seeds_v1_lib import normalize_snippet, snippet_hash

_TEMPLATE_ID_RE = re.compile(r"^zf_t(\d+)$", re.IGNORECASE)


def _production_template_num(template_id: str) -> int | None:
    m = _TEMPLATE_ID_RE.match(str(template_id))
    if not m:
        return None
    return int(m.group(1))


def next_production_template_id(existing_rows: list[dict[str, Any]]) -> str:
    max_n = 0
    for row in existing_rows:
        n = _production_template_num(str(row.get("template_id") or ""))
        if n is not None:
            max_n = max(max_n, n)
    return f"zf_t{max_n + 1:02d}"


def production_row_from_prospect(prospect: dict[str, Any], *, template_id: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "template_id": template_id,
        "shard_id": str(prospect.get("shard_id") or "zone_f_code"),
        "language": str(prospect.get("language") or "python"),
        "snippet": normalize_snippet(str(prospect.get("snippet") or "")),
        "must_keep_terms": list(prospect.get("must_keep_terms") or []),
    }
    if prospect.get("source_row_id"):
        row["merged_from_prospect_id"] = str(prospect.get("template_id") or "")
        row["source_row_id"] = prospect.get("source_row_id")
    return row


def plan_prospect_merge(
    *,
    production_rows: list[dict[str, Any]],
    prospect_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    existing_snippets = {normalize_snippet(str(r.get("snippet") or "")) for r in production_rows}
    existing_hashes = {snippet_hash(s) for s in existing_snippets if s}
    to_merge: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    working = list(production_rows)
    for prospect in prospect_rows:
        snippet = normalize_snippet(str(prospect.get("snippet") or ""))
        if not snippet:
            skipped.append({**prospect, "skip_reason": "empty_snippet"})
            continue
        h = snippet_hash(snippet)
        if snippet in existing_snippets or h in existing_hashes:
            skipped.append({**prospect, "skip_reason": "duplicate_snippet"})
            continue
        new_id = next_production_template_id(working)
        prod_row = production_row_from_prospect(prospect, template_id=new_id)
        to_merge.append(
            {
                "prospect_template_id": prospect.get("template_id"),
                "new_template_id": new_id,
                "snippet_sha256": h,
                "production_row": prod_row,
            }
        )
        working.append(prod_row)
        existing_snippets.add(snippet)
        existing_hashes.add(h)
    merged_rows = list(production_rows) + [m["production_row"] for m in to_merge]
    return {
        "production_before_count": len(production_rows),
        "prospect_input_count": len(prospect_rows),
        "merge_count": len(to_merge),
        "skipped_count": len(skipped),
        "production_after_count": len(merged_rows),
        "to_merge": to_merge,
        "skipped": skipped,
        "merged_rows": merged_rows,
    }


def write_catalog_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def load_catalog_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return load_template_catalog(path)
