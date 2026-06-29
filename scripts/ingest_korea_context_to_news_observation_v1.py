#!/usr/bin/env python3
"""Ingest Korea disaster context articles (Exa/Naver pool) into news_observation_v1 JSONL.

Reads ``reports/korea_disaster_news_articles_v1.json`` (from build_korea_disaster_news_context_v1.py)
and appends normalized rows to the B-track news observation ledger.

research_only · point-in-time · not for A-track or live triggers.
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
DEFAULT_ARTICLES = ROOT / "reports/korea_disaster_news_articles_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pub_as_of_utc(pub_date: str) -> tuple[str, str]:
    """Published start-of-day UTC; as_of end-of publication day (point-in-time)."""
    d = str(pub_date or "")[:10]
    if len(d) != 10:
        now = _utc_now()
        return now, now
    published = f"{d}T00:00:00Z"
    as_of = f"{d}T23:59:59Z"
    return published, as_of


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _row_key(row: dict[str, Any]) -> str:
    url = str(row.get("source_record_url") or "")
    if url:
        return f"url:{url}"
    return f"txt:{row.get('text_sha256', '')}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--articles-json", type=Path, default=DEFAULT_ARTICLES)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dataset-partition", default="train_holdout")
    ap.add_argument("--hypothesis-tag", default="[HYPO]")
    ap.add_argument(
        "--source-id-prefix",
        default="korea_disaster",
        help="Prefix for source_id (e.g. korea_health for H-PL1 infectious lane).",
    )
    ap.add_argument("--validate", action="store_true")
    ns = ap.parse_args()

    if not ns.articles_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing {ns.articles_json}"}), file=sys.stderr)
        return 2

    doc = _load_json(ns.articles_json)
    articles = doc.get("articles") or []
    if not isinstance(articles, list):
        articles = []

    ingested = _utc_now()
    built: list[dict[str, Any]] = []
    for a in articles:
        if not isinstance(a, dict):
            continue
        title = str(a.get("title") or "").strip()
        if not title:
            continue
        pub = str(a.get("pub_date") or "")[:10]
        published, as_of = _pub_as_of_utc(pub)
        api = str(a.get("source_api") or "korea_context").strip().lower()
        canonical = title
        link = str(a.get("link") or "").strip()
        row: dict[str, Any] = {
            "schema_version": "news_observation_v1",
            "observation_id": str(uuid.uuid4()),
            "as_of_utc": as_of,
            "published_utc": published,
            "source_id": f"{ns.source_id_prefix}_{api}",
            "canonical_text": canonical,
            "text_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "ingested_at_utc": ingested,
            "dataset_partition": ns.dataset_partition,
            "hypothesis_tag": ns.hypothesis_tag,
        }
        if link:
            row["source_record_url"] = link
        built.append(row)

    merged: dict[str, dict[str, Any]] = {}
    for row in _load_jsonl(ns.output_jsonl):
        if row.get("schema_version") == "news_observation_v1":
            merged[_row_key(row)] = row
    for row in built:
        merged[_row_key(row)] = row

    out_rows = sorted(
        merged.values(),
        key=lambda r: (str(r.get("as_of_utc") or ""), str(r.get("observation_id") or "")),
    )
    ns.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    ns.output_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows) + ("\n" if out_rows else ""),
        encoding="utf-8",
    )

    meta = {
        "ok": True,
        "schema": "ingest_korea_context_to_news_observation_v1",
        "articles_json": str(ns.articles_json.resolve()),
        "output_jsonl": str(ns.output_jsonl.resolve()),
        "built_rows": len(built),
        "output_rows": len(out_rows),
    }
    print(json.dumps(meta, ensure_ascii=False))

    if ns.validate and out_rows:
        val = ROOT / "scripts/validate_news_observation_jsonl_v1.py"
        pr = subprocess.run(
            [sys.executable, str(val), "--news-jsonl", str(ns.output_jsonl)],
            cwd=str(ROOT),
        )
        return pr.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
