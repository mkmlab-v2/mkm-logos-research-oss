#!/usr/bin/env python3
"""Harvest IJEOMA chunk-table JSONL rows into compression eval cases (B-track)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TABLE = ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"


def _shorten(text: str, ratio: float = 0.55) -> str:
    words = text.split()
    if not words:
        return text
    keep = max(1, int(len(words) * ratio))
    return " ".join(words[:keep])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-cases", type=int, default=86)
    ap.add_argument("--min-chars", type=int, default=40)
    ap.add_argument(
        "--canonical",
        type=Path,
        default=None,
        help="Merged UTF-8 TXT; join line_start..line_end per chunk row (IJEOMA spec).",
    )
    args = ap.parse_args()

    table_path = (ROOT / args.table).resolve() if not args.table.is_absolute() else args.table.resolve()
    out_path = (ROOT / args.out).resolve() if not args.out.is_absolute() else args.out.resolve()
    if not table_path.is_file():
        print(json.dumps({"error": "table_missing", "path": str(table_path)}, ensure_ascii=False))
        return 2

    lines: list[str] | None = None
    canon_resolved: Path | None = None
    canon_path = args.canonical
    if canon_path is None:
        manifest = ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json"
        if manifest.is_file():
            rel = json.loads(manifest.read_text(encoding="utf-8")).get("canonical_source", {}).get(
                "path_workspace"
            )
            if rel:
                canon_path = ROOT / str(rel)
    if canon_path is not None:
        canon_resolved = (ROOT / canon_path).resolve() if not canon_path.is_absolute() else canon_path.resolve()
        if canon_resolved.is_file():
            lines = canon_resolved.read_text(encoding="utf-8", errors="replace").splitlines()
        else:
            canon_resolved = None

    cases: list[dict] = []
    with table_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = ""
            if lines is not None:
                ls = int(row.get("line_start") or 0)
                le = int(row.get("line_end") or 0)
                if ls >= 1 and le >= ls:
                    text = "".join(lines[ls - 1 : le])
            if not text:
                text = str(
                    row.get("text")
                    or row.get("chunk_text")
                    or row.get("content")
                    or row.get("preview_80chars")
                    or ""
                ).strip()
            if len(text) < args.min_chars:
                continue
            cid = str(row.get("chunk_id") or row.get("id") or f"chunk_{len(cases)+1:04d}")
            comp = _shorten(text)
            cases.append(
                {
                    "id": f"ijeoma_chunk_{cid}",
                    "raw_text": text,
                    "compressed_text": comp,
                    "reconstructed_text": comp,
                    "domain": "ijeoma_sasang",
                    "source_path": str(table_path.relative_to(ROOT)).replace("\\", "/"),
                    "chunk_id": cid,
                }
            )
            if len(cases) >= max(1, args.max_cases):
                break

    out_doc = {
        "schema": "multilens_performance_eval_input_v1",
        "description": "IJEOMA chunk-table harvest for Universal Matrix merge.",
        "research_only": True,
        "boundary_ack": "B-track [HYPO] — chunk table rows; not clinical advice",
        "compression_cases": cases,
        "domain_tag": "ijeoma_sasang",
        "lane_id": "ijeoma_chunk_table_v1",
        "source_table": str(table_path.relative_to(ROOT)).replace("\\", "/"),
        "canonical_source": (
            str(canon_resolved.relative_to(ROOT)).replace("\\", "/")
            if lines is not None and canon_path is not None
            else None
        ),
        "eval_contract": "full_chunk_join" if lines is not None else "preview_fallback",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out_path.relative_to(ROOT)), "case_count": len(cases)}, ensure_ascii=False))
    return 0 if cases else 1


if __name__ == "__main__":
    raise SystemExit(main())
