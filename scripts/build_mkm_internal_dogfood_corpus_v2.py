#!/usr/bin/env python3
"""Build longer LLM-context MKM internal dogfood JSONL (Tactical A v2).

Sources: finance/macro B2B eval paragraphs, open structured long API payloads,
and stitched internal governance prose — paths scrubbed; corpus is local-only.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/compression/mkm_internal_dogfood_v2.jsonl"
META_OUT = ROOT / "reports/mkm_internal_dogfood_corpus_build_v2_latest.json"

_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s\"']+")
_UNIX_PATH_RE = re.compile(r"/(?:workspace|home|Users)/[^\s\"']+")
_DOCS_PATH_RE = re.compile(r"docs/final/[^\s\"']+")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _scrub(text: str) -> str:
    s = text
    s = _PATH_RE.sub("[PATH]", s)
    s = _UNIX_PATH_RE.sub("[PATH]", s)
    s = _DOCS_PATH_RE.sub("[DOC]", s)
    s = _EMAIL_RE.sub("[EMAIL]", s)
    s = s.replace("C:\\workspace", "[WORKSPACE]").replace("c:/workspace", "[WORKSPACE]")
    s = s.replace("C:/workspace", "[WORKSPACE]")
    return s.strip()


def _row(text: str, *, domain_tag: str, source: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "text": _scrub(text),
        "domain_tag": domain_tag,
        "source": source,
        "dogfood": True,
        "dogfood_version": "v2",
        "pii_scrubbed": True,
    }
    if extra:
        out.update(extra)
    return out


def _from_finance_macro(*, min_chars: int, max_rows: int) -> list[dict[str, Any]]:
    path = ROOT / "docs/final/artifacts/finance_macro_b2b_compression_eval_input_v1.json"
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    cases = sorted(
        doc.get("compression_cases") or [],
        key=lambda c: len(str(c.get("raw_text") or "")),
        reverse=True,
    )
    rows: list[dict[str, Any]] = []
    for case in cases:
        raw = str(case.get("raw_text") or "").strip()
        if len(raw) < min_chars:
            continue
        rows.append(
            _row(
                raw,
                domain_tag=str(case.get("domain") or "finance_macro_b2b"),
                source="finance_macro_b2b_compression_eval_input",
                extra={"case_id": case.get("id")},
            )
        )
        if len(rows) >= max_rows:
            break
    return rows


def _from_open_structured_long(*, max_rows: int) -> list[dict[str, Any]]:
    path = ROOT / "data/compression/stateless_poc_open_structured_long_v1.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        text = str(obj.get("text") or "").strip()
        if not text:
            continue
        rows.append(
            _row(
                text,
                domain_tag=str(obj.get("domain_tag") or "open_structured_long"),
                source="stateless_poc_open_structured_long_v1",
                extra={"open_id": obj.get("id")},
            )
        )
        if len(rows) >= max_rows:
            break
    return rows


def _from_stitched_governance_blocks(*, max_rows: int) -> list[dict[str, Any]]:
    """Stitch short eval lines into LLM-sized context blocks (internal prose only)."""
    path = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    lines = [str(c.get("raw_text") or "").strip() for c in doc.get("compression_cases") or []]
    lines = [ln for ln in lines if ln]
    rows: list[dict[str, Any]] = []
    chunk = 5
    for i in range(0, len(lines), chunk):
        block = "\n\n".join(lines[i : i + chunk])
        if len(block) < 280:
            continue
        rows.append(
            _row(
                block,
                domain_tag="internal_eval_stitch",
                source="multilens_performance_eval_input_v2_stitch",
                extra={"block_index": i // chunk},
            )
        )
        if len(rows) >= max_rows:
            break
    return rows


def build_corpus(*, target_rows: int = 24) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    buckets = [
        _from_finance_macro(min_chars=180, max_rows=12),
        _from_open_structured_long(max_rows=8),
        _from_stitched_governance_blocks(max_rows=4),
    ]
    merged: list[dict[str, Any]] = []
    for b in buckets:
        merged.extend(b)
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for r in merged:
        key = r["text"][:160]
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    unique.sort(key=lambda r: len(r["text"]), reverse=True)
    unique = unique[: max(20, min(target_rows, len(unique)))]
    char_lens = [len(r["text"]) for r in unique]
    meta = {
        "schema": "mkm_internal_dogfood_corpus_build_v2",
        "generated_at_utc": _utc(),
        "row_count": len(unique),
        "char_len_min": min(char_lens) if char_lens else 0,
        "char_len_max": max(char_lens) if char_lens else 0,
        "char_len_mean": round(sum(char_lens) / len(char_lens), 1) if char_lens else 0,
        "sources": [
            "finance_macro_b2b_compression_eval_input",
            "stateless_poc_open_structured_long_v1",
            "multilens_performance_eval_input_v2_stitch",
        ],
        "labels": ["dogfood", "internal_llm_context", "pii_scrubbed", "git_commit_forbidden"],
        "tenant_recommendation": "mkm-internal-dogfood-v2",
        "note": "Long-context dogfood; not Track A Golden40; SEND_GATE HOLD",
    }
    return unique, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-json", type=Path, default=META_OUT)
    ap.add_argument("--rows", type=int, default=24)
    args = ap.parse_args()
    rows, meta = build_corpus(target_rows=args.rows)
    if len(rows) < 20:
        print(json.dumps({"ok": False, "error": "insufficient_rows", "rows": len(rows)}, ensure_ascii=False))
        return 1
    out = args.out_jsonl if args.out_jsonl.is_absolute() else ROOT / args.out_jsonl
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    meta["out_jsonl"] = str(out.relative_to(ROOT)).replace("\\", "/")
    meta_path = args.meta_json if args.meta_json.is_absolute() else ROOT / args.meta_json
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows), "out_jsonl": meta["out_jsonl"], **meta}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
