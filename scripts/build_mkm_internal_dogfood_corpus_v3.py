#!/usr/bin/env python3
"""Build metering-adjacent long LLM context dogfood JSONL (Tactical A v3).

Each row wraps scrubbed internal prose in a pseudo API/metering envelope so the
pilot path resembles production token metering context — local-only, gitignored.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/compression/mkm_internal_dogfood_v3.jsonl"
META_OUT = ROOT / "reports/mkm_internal_dogfood_corpus_build_v3_latest.json"

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
    for old in ("C:\\workspace", "c:/workspace", "C:/workspace"):
        s = s.replace(old, "[WORKSPACE]")
    return s.strip()


def _row(text: str, *, domain_tag: str, source: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "text": _scrub(text),
        "domain_tag": domain_tag,
        "source": source,
        "dogfood": True,
        "dogfood_version": "v3",
        "metering_adjacent": True,
        "pii_scrubbed": True,
    }
    if extra:
        out.update(extra)
    return out


def _envelope(*, request_id: str, domain: str, body_text: str) -> str:
    payload = {
        "meter_schema": "track_a_metering_log_v1",
        "eval_context": {
            "client_request_id": request_id,
            "sla_track": "active",
            "domain": domain,
            "notes": "dogfood_v3_metering_adjacent_envelope",
        },
        "messages": [
            {"role": "system", "content": "MKM compression pilot — internal dogfood context only; SEND_GATE HOLD."},
            {"role": "user", "content": body_text},
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def _finance_paragraphs(*, min_chars: int, max_rows: int) -> list[str]:
    path = ROOT / "docs/final/artifacts/finance_macro_b2b_compression_eval_input_v1.json"
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    cases = sorted(
        doc.get("compression_cases") or [],
        key=lambda c: len(str(c.get("raw_text") or "")),
        reverse=True,
    )
    out: list[str] = []
    for case in cases:
        raw = str(case.get("raw_text") or "").strip()
        if len(raw) < min_chars:
            continue
        out.append(raw)
        if len(out) >= max_rows:
            break
    return out


def _open_structured_bodies(*, max_rows: int) -> list[str]:
    path = ROOT / "data/compression/stateless_poc_open_structured_long_v1.jsonl"
    if not path.is_file():
        return []
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        text = str(obj.get("text") or "").strip()
        if text:
            out.append(text)
        if len(out) >= max_rows:
            break
    return out


def _mock_thread_blocks(*, max_rows: int) -> list[str]:
    path = ROOT / "data/compression/mock_customer_pilot_v1.jsonl"
    if not path.is_file():
        return []
    lines = [json.loads(ln)["text"] for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    blocks: list[str] = []
    chunk = 4
    for i in range(0, len(lines), chunk):
        block = "\n".join(lines[i : i + chunk])
        if len(block) >= 120:
            blocks.append(block)
        if len(blocks) >= max_rows:
            break
    return blocks


def build_corpus(*, target_rows: int = 24) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bodies: list[tuple[str, str, str]] = []
    for i, p in enumerate(_finance_paragraphs(min_chars=200, max_rows=10)):
        bodies.append((p, "finance_macro_b2b", f"fin-{i:03d}"))
    for i, p in enumerate(_open_structured_bodies(max_rows=8)):
        bodies.append((p, "open_structured_long", f"open-{i:03d}"))
    for i, p in enumerate(_mock_thread_blocks(max_rows=6)):
        bodies.append((p, "mock_customer_stitch", f"mock-{i:03d}"))

    rows: list[dict[str, Any]] = []
    for i, (body, src, rid) in enumerate(bodies[:target_rows]):
        env = _envelope(request_id=f"dogfood-v3-{rid}", domain=src, body_text=body)
        rows.append(
            _row(
                env,
                domain_tag="metering_llm_context",
                source="metering_adjacent_envelope_v3",
                extra={"envelope_source": src, "body_chars": len(body)},
            )
        )

    char_lens = [len(r["text"]) for r in rows]
    meta = {
        "schema": "mkm_internal_dogfood_corpus_build_v3",
        "generated_at_utc": _utc(),
        "row_count": len(rows),
        "char_len_min": min(char_lens) if char_lens else 0,
        "char_len_max": max(char_lens) if char_lens else 0,
        "char_len_mean": round(sum(char_lens) / len(char_lens), 1) if char_lens else 0,
        "sources": [
            "finance_macro_b2b_compression_eval_input",
            "stateless_poc_open_structured_long_v1",
            "mock_customer_pilot_v1_stitch",
        ],
        "labels": ["dogfood", "metering_adjacent", "internal_llm_context", "git_commit_forbidden"],
        "tenant_recommendation": "mkm-internal-dogfood-v3",
        "note": "Metering-style JSON envelope over long body; not Track A Golden40; SEND_GATE HOLD",
    }
    return rows, meta


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
