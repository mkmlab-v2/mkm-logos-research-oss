# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.48, L:0.60, K:0.80, M:0.38}
# Balance: 84
# Purpose: SASANG_CROSS_REF_DRAFT entry_id / chunk / line deep links for clinical lens.
"""sasang_cross_ref_deep_link_v1 — 원전 교차 초안 행 단위 포인터."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
CROSS_REF_DRAFT = _ROOT / "docs" / "final" / "artifacts" / "SASANG_CROSS_REF_DRAFT.json"

CONSTITUTION_ID_TO_SECTION: dict[str, str] = {
    "soeum_in": "soeum",
    "soyang_in": "soyang",
    "taeeum_in": "taeeum",
    "taeyang_in": "taeyang",
}


def _deep_link_uri(entry_id: str, chunk_id: str, line_start: int, line_end: int) -> str:
    return f"sasang_cross_ref://{entry_id}?chunk={chunk_id}&lines={line_start}-{line_end}"


@lru_cache(maxsize=2)
def _load_cross_ref(path_str: str) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    path = Path(path_str)
    if not path.is_file():
        return (), {"status": "missing"}
    doc = json.loads(path.read_text(encoding="utf-8"))
    entries = doc.get("entries") or []
    if not isinstance(entries, list):
        return (), {"status": "invalid"}
    clean = [e for e in entries if isinstance(e, dict) and e.get("entry_id")]
    return tuple(clean), {
        "status": "ok",
        "chunk_table_ssot": doc.get("chunk_table_ssot"),
        "entry_count": len(clean),
    }


def deep_links_for_constitution(
    constitution_id: str,
    *,
    cross_ref_path: Path | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Top confidence rows for section_key; B-track analogy_bench only."""
    section = CONSTITUTION_ID_TO_SECTION.get(constitution_id)
    if not section:
        return []
    p = cross_ref_path or CROSS_REF_DRAFT
    entries, meta = _load_cross_ref(str(p.resolve()))
    if meta.get("status") != "ok":
        return []
    rows = [e for e in entries if str(e.get("section_key")) == section]
    rows.sort(key=lambda x: (-float(x.get("confidence") or 0), str(x.get("entry_id", ""))))
    out: list[dict[str, Any]] = []
    for e in rows[: max(1, limit)]:
        ls = int(e.get("line_start") or 0)
        le = int(e.get("line_end") or ls)
        cid = str(e.get("chunk_id") or "")
        eid = str(e.get("entry_id") or "")
        out.append(
            {
                "entry_id": eid,
                "chunk_id": cid,
                "section_key": section,
                "section_label": e.get("section_label"),
                "line_start": ls,
                "line_end": le,
                "artifact_path": e.get("artifact_path") or meta.get("chunk_table_ssot"),
                "satellite_ref": e.get("satellite_ref"),
                "link_type": e.get("link_type"),
                "confidence": e.get("confidence"),
                "deep_link_uri": _deep_link_uri(eid, cid, ls, le),
                "note_ko": "[HYPO] analogy_bench — 임상·처방 SSOT 아님",
            }
        )
    return out


def render_deep_links_markdown(links: list[dict[str, Any]]) -> str:
    if not links:
        return "- *(해당 section_key 교차 행 없음)*"
    lines: list[str] = []
    for lk in links:
        lines.append(
            f"- `{lk.get('entry_id')}` · {lk.get('section_label') or lk.get('section_key')} "
            f"(L{lk.get('line_start')}–{lk.get('line_end')}, conf={lk.get('confidence')})"
        )
        lines.append(f"  - chunk: `{lk.get('chunk_id')}`")
        lines.append(f"  - deep: `{lk.get('deep_link_uri')}`")
        sat = lk.get("satellite_ref")
        if sat:
            lines.append(f"  - ref: {sat}")
    return "\n".join(lines)
