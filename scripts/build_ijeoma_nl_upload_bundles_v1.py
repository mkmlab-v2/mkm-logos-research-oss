#!/usr/bin/env python3
"""Build NL upload bundles: section canon + chunk-id text batches for IJEOMA notebook."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "docs/sasang-origin/정교동의수세보원원문.txt"
MANIFEST = ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json"
CHUNK_TABLE = ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"
OUT = ROOT / "reports/ijeoma_nl_upload_bundles_v1"
HEADER = (
    "[HYPO] B-track IJEOMA canon bundle · not clinical prescription · send_gate HOLD\n\n"
)


def _join_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    lines = CANON.read_text(encoding="utf-8").splitlines()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    index: dict = {"schema": "ijeoma_nl_upload_bundles_v1", "files": []}

    sec_dir = OUT / "sections"
    sec_dir.mkdir(exist_ok=True)
    for sec in manifest.get("sections_v0", []):
        key = sec["section_key"]
        body = _join_lines(lines, int(sec["line_start"]), int(sec["line_end"]))
        name = f"canon_section_{key}.txt"
        path = sec_dir / name
        text = (
            HEADER
            + f"# section_key={key} label={sec.get('label', '')}\n"
            + f"# lines {sec['line_start']}-{sec['line_end']}\n\n"
            + body
        )
        path.write_text(text, encoding="utf-8")
        index["files"].append({"kind": "section", "path": str(path.relative_to(ROOT)), "chars": len(text)})

    chunks = [json.loads(ln) for ln in CHUNK_TABLE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    batch_size = 25
    chunk_dir = OUT / "chunk_batches"
    chunk_dir.mkdir(exist_ok=True)
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        parts: list[str] = [
            HEADER + f"# chunk batch {i // batch_size + 1} ({len(batch)} chunks)\n"
        ]
        for row in batch:
            ls, le = int(row["line_start"]), int(row["line_end"])
            text = _join_lines(lines, ls, le)
            parts.append(f"\n<!-- {row['chunk_id']} section={row.get('section_key')} -->\n{text}\n")
        name = f"canon_chunks_batch_{i // batch_size + 1:03d}.txt"
        path = chunk_dir / name
        body = "".join(parts)
        path.write_text(body, encoding="utf-8")
        index["files"].append(
            {"kind": "chunk_batch", "path": str(path.relative_to(ROOT)), "chars": len(body), "n_chunks": len(batch)}
        )

    (OUT / "bundle_index_v1.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "section_files": len(manifest.get("sections_v0", [])), "chunk_batches": (len(chunks) + batch_size - 1) // batch_size}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
