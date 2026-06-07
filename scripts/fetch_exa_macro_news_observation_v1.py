#!/usr/bin/env python3
"""[HYPO] PoC: Exa global macro search → news_observation_v1 JSONL staging (B-track only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl"
DEFAULT_META = ROOT / "reports/exa_macro_news_fetch_v1_latest.json"
DEFAULT_QUERY = (
    "global macro markets central bank inflation oil geopolitical risk-off risk-on latest"
)
EXA_SEARCH_URL = "https://api.exa.ai/search"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_published(raw: Any) -> str:
    if not raw:
        return _utc_now()
    s = str(raw).strip()
    if s.endswith("Z"):
        return s
    if "T" in s:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass
    return _utc_now()


def _row_from_exa_result(item: dict[str, Any], *, ingested_at: str) -> dict[str, Any]:
    title = _normalize_text(item.get("title") or "")
    body = _normalize_text(item.get("text") or item.get("summary") or "")
    canonical = _normalize_text(f"{title}. {body}" if body else title)
    if not canonical:
        canonical = _normalize_text(item.get("url") or "exa_result")
    published = _parse_published(item.get("publishedDate") or item.get("published_date"))
    return {
        "schema_version": "news_observation_v1",
        "observation_id": str(uuid.uuid4()),
        "as_of_utc": published,
        "published_utc": published,
        "source_id": "exa_macro_wire",
        "source_record_url": str(item.get("url") or item.get("id") or "https://exa.invalid/unknown"),
        "canonical_text": canonical[:4000],
        "text_sha256": _sha256(canonical[:4000]),
        "ingested_at_utc": ingested_at,
        "dataset_partition": "calibration",
        "hypothesis_tag": "[HYPO]",
    }


def _exa_search(query: str, *, num_results: int, api_key: str) -> dict[str, Any]:
    payload = {
        "query": query,
        "numResults": num_results,
        "type": "auto",
        "contents": {"text": {"maxCharacters": 1200}},
    }
    req = urllib.request.Request(
        EXA_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _rows_from_fixture(doc: dict[str, Any], *, ingested_at: str) -> list[dict[str, Any]]:
    results = doc.get("results") or []
    return [_row_from_exa_result(r, ingested_at=ingested_at) for r in results if isinstance(r, dict)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--num-results", type=int, default=8)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-json", type=Path, default=DEFAULT_META)
    ap.add_argument("--fixture-json", type=Path, help="Offline Exa-like response (skip network)")
    ap.add_argument("--append", action="store_true", help="Append to output JSONL instead of overwrite")
    ap.add_argument("--validate", action="store_true", help="Run validate_news_observation_jsonl_v1.py")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ingested_at = _utc_now()
    if args.fixture_json:
        doc = json.loads(args.fixture_json.read_text(encoding="utf-8"))
        rows = _rows_from_fixture(doc, ingested_at=ingested_at)
        source = "fixture"
    else:
        api_key = os.environ.get("EXA_API_KEY", "").strip()
        if not api_key:
            print("ERROR: EXA_API_KEY not set; use --fixture-json for offline PoC.", file=sys.stderr)
            return 2
        if args.dry_run:
            print(f"DRY-RUN exa query={args.query!r} num={args.num_results}")
            return 0
        try:
            doc = _exa_search(args.query, num_results=args.num_results, api_key=api_key)
        except urllib.error.HTTPError as exc:
            print(f"ERROR: Exa HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}", file=sys.stderr)
            return 2
        except urllib.error.URLError as exc:
            print(f"ERROR: Exa network: {exc.reason}", file=sys.stderr)
            return 2
        rows = _rows_from_fixture(doc, ingested_at=ingested_at)
        source = "exa_api"

    if not rows:
        print("ERROR: no rows materialized", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append else "w"
    with args.output.open(mode, encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    meta = {
        "schema": "exa_macro_news_fetch_v1",
        "generated_at_utc": ingested_at,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "source": source,
        "query": args.query,
        "num_results_requested": args.num_results,
        "rows_written": len(rows),
        "output_jsonl": str(args.output),
        "boundary_ack": "B-track ingest only; not A-track or live trigger.",
    }
    args.meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} ({len(rows)} rows)")
    print(f"META: {args.meta_json.resolve()}")

    if args.validate:
        val = ROOT / "scripts/validate_news_observation_jsonl_v1.py"
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(val), "--news-jsonl", str(args.output)],
            cwd=str(ROOT),
        )
        return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
