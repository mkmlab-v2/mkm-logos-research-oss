#!/usr/bin/env python3
"""Build biblical-history research news slice (2026 dates) without overwriting production JSONL."""

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
DEFAULT_KOREA = ROOT / "reports/korea_disaster_news_articles_v1.json"
DEFAULT_HEALTH = ROOT / "reports/korea_health_infectious_news_articles_v1.json"
DEFAULT_COVID_FIXTURE = ROOT / "tests/fixtures/biblical_resonance_covid_window_news_smoke_v1.jsonl"
DEFAULT_SMOKE = ROOT / "tests/fixtures/biblical_resonance_research_news_smoke_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/news_observation_v1_biblical_history_research_slice_latest.jsonl"
DEFAULT_PROD = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_DSS_CONTEXT = ROOT / "docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl"
DEFAULT_NDJSON_CONTEXT = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_research_context_latest.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _from_korea_article(article: dict[str, Any], ingested: str) -> dict[str, Any] | None:
    title = str(article.get("title") or "").strip()
    if not title:
        return None
    pub = str(article.get("pub_date") or "")[:10]
    if len(pub) != 10:
        return None
    published = f"{pub}T00:00:00Z"
    as_of = f"{pub}T23:59:59Z"
    link = str(article.get("link") or "").strip()
    canonical = title
    text_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    api = str(article.get("source_api") or "korea_context").strip().lower()
    return {
        "schema_version": "news_observation_v1",
        "observation_id": str(uuid.uuid4()),
        "as_of_utc": as_of,
        "published_utc": published,
        "source_id": f"korea_context_{api}",
        "canonical_text": canonical,
        "text_sha256": text_sha,
        "ingested_at_utc": ingested,
        "dataset_partition": "biblical_history_research_slice",
        "hypothesis_tag": "[HYPO]",
        "source_record_url": link or None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--korea-articles-json", type=Path, default=DEFAULT_KOREA)
    ap.add_argument("--health-articles-json", type=Path, default=DEFAULT_HEALTH)
    ap.add_argument("--covid-fixture-jsonl", type=Path, default=DEFAULT_COVID_FIXTURE)
    ap.add_argument("--smoke-jsonl", type=Path, default=DEFAULT_SMOKE)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-korea-rows", type=int, default=120)
    ap.add_argument("--run-resonance-eval", action="store_true")
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--dss-context-jsonl", type=Path, default=DEFAULT_DSS_CONTEXT)
    ap.add_argument("--ndjson-context-jsonl", type=Path, default=DEFAULT_NDJSON_CONTEXT)
    ap.add_argument("--skip-dss-context", action="store_true")
    ap.add_argument("--skip-ndjson-context", action="store_true")
    ap.add_argument(
        "--skip-korea-context",
        action="store_true",
        help="Omit Korea disaster/health article feeds (reduces prod ledger text_sha256 overlap in isolated AB).",
    )
    args = ap.parse_args()

    ingested = _utc_now()
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for context_path in (
        [] if args.skip_dss_context else [args.dss_context_jsonl],
        [] if args.skip_ndjson_context else [args.ndjson_context_jsonl],
    ):
        for path in context_path:
            if not path.is_file():
                continue
            for row in _load_jsonl(path):
                key = _row_key(row)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(row)

    for path in (args.smoke_jsonl, args.covid_fixture_jsonl):
        for row in _load_jsonl(path):
            key = _row_key(row)
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)

    if not args.skip_korea_context:
        for articles_path in (args.korea_articles_json, args.health_articles_json):
            if not articles_path.is_file():
                continue
            doc = _load_json(articles_path)
            articles = doc.get("articles") if isinstance(doc.get("articles"), list) else []
            for article in articles[: max(0, args.max_korea_rows)]:
                if not isinstance(article, dict):
                    continue
                row = _from_korea_article(article, ingested)
                if row is None:
                    continue
                key = _row_key(row)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(row)

    merged.sort(key=lambda r: str(r.get("as_of_utc") or ""))
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + ("\n" if merged else ""),
        encoding="utf-8",
    )

    summary = {
        "ok": True,
        "output_jsonl": str(args.output_jsonl),
        "row_count": len(merged),
        "production_jsonl_preserved": str(DEFAULT_PROD),
        "slice_flags": {
            "skip_dss_context": args.skip_dss_context,
            "skip_ndjson_context": args.skip_ndjson_context,
            "skip_korea_context": args.skip_korea_context,
            "max_korea_rows": 0 if args.skip_korea_context else args.max_korea_rows,
        },
        "note": "Research slice only; production refresh chain is Run-LogosNewsObservationChain_v1.ps1",
    }
    print(json.dumps(summary, ensure_ascii=False))

    if args.run_resonance_eval:
        out_eval = ROOT / "reports/biblical_resonance_eval_research_slice_latest.json"
        cmd = [
            sys.executable,
            str(ROOT / "scripts/evaluate_biblical_resonance_hypotheses_v1.py"),
            "--news-jsonl",
            str(args.output_jsonl),
            "--lookback-days",
            str(args.lookback_days),
            "--output-json",
            str(out_eval),
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
        return int(proc.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
