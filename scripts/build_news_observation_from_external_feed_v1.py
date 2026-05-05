#!/usr/bin/env python3
"""Build news_observation_v1 JSONL from external_feed_drop_v1 JSON.

Research-only ingest bridge:
- Reads external feed drop JSON (`data` list)
- Extracts text/time/url fields conservatively
- Emits news_observation_v1 rows with non-synthetic source_id
- Optionally appends to an existing news JSONL and validates output
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTERNAL_FEED = ROOT / "docs" / "final" / "artifacts" / "external_feed_drop_latest.validated.json"
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_latest.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso_or_none(value: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
        dt = datetime.fromisoformat(candidate)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _pick_first_str(item: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _flatten_text(item: Any) -> list[str]:
    if isinstance(item, str):
        s = item.strip()
        return [s] if s else []
    if not isinstance(item, dict):
        return []
    acc: list[str] = []
    for key in ("headline", "title", "summary", "description", "text", "body", "snippet", "content"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            acc.append(value.strip())
    for value in item.values():
        acc.extend(_flatten_text(value))
    return acc


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _row_key(row: dict[str, Any]) -> str:
    obs = str(row.get("observation_id") or "").strip()
    if obs:
        return f"obs:{obs}"
    txt = str(row.get("canonical_text") or "").strip()
    as_of = str(row.get("as_of_utc") or "").strip()
    return f"fallback:{as_of}:{hashlib.sha256(txt.encode('utf-8')).hexdigest()}"


def main() -> int:
    ap = argparse.ArgumentParser(description="external_feed_drop_v1 -> news_observation_v1 JSONL")
    ap.add_argument("--external-feed-json", type=Path, default=DEFAULT_EXTERNAL_FEED)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--append-existing-jsonl", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--dataset-partition", type=str, default="train_holdout")
    ap.add_argument("--hypothesis-tag", type=str, default="[HYPO]")
    ap.add_argument("--source-id-prefix", type=str, default="external_feed")
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()

    src_path = Path(args.external_feed_json).resolve()
    out_path = Path(args.output_jsonl).resolve()
    append_path = Path(args.append_existing_jsonl).resolve()
    if not src_path.is_file():
        print(f"ERROR: missing external feed json: {src_path}", file=sys.stderr)
        return 1

    doc = _load_json(src_path)
    data = doc.get("data")
    if not isinstance(data, list):
        data = []
    provider = str((doc.get("source") or {}).get("provider") or "unknown").strip().lower() or "unknown"
    source_id = f"{args.source_id_prefix}_{provider}"
    generated_at = _parse_iso_or_none(str(doc.get("generated_at_utc") or "")) or _utc_now_iso()
    ingested = _utc_now_iso()

    built_rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        headline = _pick_first_str(item, ["headline", "title"])
        summary = _pick_first_str(item, ["summary", "description", "snippet"])
        body = _pick_first_str(item, ["text", "body", "content"])
        text_parts = [x for x in [headline, summary, body] if x]
        if not text_parts:
            flat = _flatten_text(item)
            if flat:
                text_parts = [flat[0]]
        canonical_text = " | ".join(text_parts).strip()
        if not canonical_text:
            continue

        published = _parse_iso_or_none(
            _pick_first_str(item, ["published_utc", "published_at", "publishedAt", "timestamp", "time"])
        ) or generated_at
        as_of = _parse_iso_or_none(_pick_first_str(item, ["as_of_utc", "asOfUtc"])) or published
        url = _pick_first_str(item, ["url", "link", "source_url", "source_record_url"])

        row: dict[str, Any] = {
            "schema_version": "news_observation_v1",
            "observation_id": str(item.get("id") or item.get("observation_id") or uuid.uuid4()),
            "as_of_utc": as_of,
            "published_utc": published,
            "source_id": source_id,
            "canonical_text": canonical_text,
            "text_sha256": hashlib.sha256(canonical_text.encode("utf-8")).hexdigest(),
            "ingested_at_utc": ingested,
            "dataset_partition": str(args.dataset_partition),
            "hypothesis_tag": str(args.hypothesis_tag),
        }
        if url:
            row["source_record_url"] = url
        built_rows.append(row)

    existing = [r for r in _load_jsonl(append_path) if r.get("schema_version") == "news_observation_v1"]
    merged: dict[str, dict[str, Any]] = {}
    for row in existing:
        merged[_row_key(row)] = row
    for row in built_rows:
        merged[_row_key(row)] = row

    output_rows = sorted(
        merged.values(),
        key=lambda x: (str(x.get("as_of_utc") or ""), str(x.get("observation_id") or "")),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in output_rows) + ("\n" if output_rows else ""),
        encoding="utf-8",
    )

    result = {
        "ok": True,
        "schema": "news_observation_external_feed_ingest_v1",
        "external_feed_json": str(src_path).replace("\\", "/"),
        "output_jsonl": str(out_path).replace("\\", "/"),
        "source_id": source_id,
        "built_rows": len(built_rows),
        "existing_rows": len(existing),
        "output_rows": len(output_rows),
    }
    print(json.dumps(result, ensure_ascii=False))

    if args.validate:
        validator = ROOT / "scripts" / "validate_news_observation_jsonl_v1.py"
        cmd = [sys.executable, str(validator), "--news-jsonl", str(out_path)]
        pr = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if pr.returncode != 0:
            print(pr.stdout)
            print(pr.stderr, file=sys.stderr)
            return pr.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

