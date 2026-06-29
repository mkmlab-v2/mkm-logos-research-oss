#!/usr/bin/env python3
"""Resolve km_classics_citation_v1 rows from km_classics_index_hypo_v1 [HYPO].

D4: On-demand / batch only — invoke from CDS chain or explicit CLI; no always-on agent.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "km_classics_citation_v1"


def _normalize_query(q: str) -> str:
    return re.sub(r"\s+", " ", (q or "").strip().lower())


def load_index(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "km_classics_index_hypo_v1":
        raise ValueError(f"unexpected_index_schema: {doc.get('schema')}")
    return doc


def resolve_classic_refs(
    index_doc: dict[str, Any],
    *,
    source_ids: list[str] | None = None,
    retrieval_query: str | None = None,
    max_refs: int = 5,
) -> list[dict[str, Any]]:
    entries = index_doc.get("entries") or []
    by_id = {e.get("source_id"): e for e in entries if e.get("source_id")}

    refs: list[dict[str, Any]] = []

    if source_ids:
        for sid in source_ids[:max_refs]:
            row = by_id.get(sid)
            refs.append(
                {
                    "source_id": sid,
                    "work": (row or {}).get("work") or sid,
                    "chapter": None,
                    "relative_path": (row or {}).get("relative_path") or "",
                    "excerpt_hash": None,
                    "retrieval_query": retrieval_query or f"source_id:{sid}",
                    "citation_valid": row is not None,
                    "read_only": True,
                }
            )
        return refs

    q = _normalize_query(retrieval_query or "")
    if not q:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in entries:
        work = str(entry.get("work") or "")
        rel = str(entry.get("relative_path") or "")
        hay = _normalize_query(f"{work} {rel}")
        score = sum(1 for token in q.split() if token and token in hay)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: (-x[0], x[1].get("relative_path") or ""))
    for _, entry in scored[:max_refs]:
        sid = str(entry.get("source_id") or "")
        refs.append(
            {
                "source_id": sid,
                "work": str(entry.get("work") or sid),
                "chapter": None,
                "relative_path": str(entry.get("relative_path") or ""),
                "excerpt_hash": None,
                "retrieval_query": retrieval_query or "",
                "citation_valid": bool(sid),
                "read_only": True,
            }
        )
    return refs


def validate_refs_schema(refs: list[dict[str, Any]], schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError as e:
        raise SystemExit("jsonschema required") from e
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for ref in refs:
        jsonschema.validate(instance=ref, schema=schema)


def main() -> int:
    import argparse

    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index-json", type=Path, required=True)
    ap.add_argument("--source-ids", default="", help="Comma-separated source_id list")
    ap.add_argument("--retrieval-query", default="")
    ap.add_argument("--max-refs", type=int, default=5)
    ap.add_argument(
        "--schema",
        type=Path,
        default=root / "docs/final/schemas/km_classics_citation_v1.schema.json",
    )
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument(
        "--audit-jsonl",
        type=Path,
        default=None,
        help="Optional JSONL audit log (query + hit ids only; no patient text)",
    )
    args = ap.parse_args()

    index_doc = load_index(args.index_json)
    ids = [x.strip() for x in args.source_ids.split(",") if x.strip()] or None
    refs = resolve_classic_refs(
        index_doc,
        source_ids=ids,
        retrieval_query=args.retrieval_query or None,
        max_refs=args.max_refs,
    )
    validate_refs_schema(refs, args.schema)

    if args.audit_jsonl is not None:
        from append_km_classics_retrieval_audit_v1 import append_audit_row, build_audit_row

        hit_ids = [str(r.get("source_id") or "") for r in refs if r.get("source_id")]
        row = build_audit_row(
            retrieval_query=args.retrieval_query or None,
            source_ids_requested=ids,
            hit_source_ids=hit_ids,
            index_path=str(args.index_json.resolve()).replace("\\", "/"),
        )
        append_audit_row(args.audit_jsonl, row)

    payload = json.dumps(refs, ensure_ascii=False, indent=2)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
