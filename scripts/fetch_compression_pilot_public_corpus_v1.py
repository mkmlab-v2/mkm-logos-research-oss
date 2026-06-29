#!/usr/bin/env python3
"""Fetch public-open corpus rows (API/RSS only) for compression pilot JSONL intake.

Sources: Hacker News Firebase API, Wikipedia REST summaries, arXiv cs.AI RSS.
NOT customer data — labels public_open / forbidden_as_customer_sla / SEND_GATE HOLD.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mkmlife.rss_minimal import parse_feed_items  # noqa: E402

DEFAULT_OUT = ROOT / "data/compression/stateless_poc_public_open_web_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/compression_public_open_corpus_fetch_v1_latest.json"

WIKI_TOPICS = [
    "Artificial_intelligence",
    "Data_compression",
    "Application_programming_interface",
    "Cloud_computing",
    "Machine_learning",
    "Information_retrieval",
    "Natural_language_processing",
    "Database",
    "Cybersecurity",
    "Software_engineering",
]

ARXIV_CS_AI_RSS = "https://export.arxiv.org/rss/cs.AI"
HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

TAG_RE = re.compile(r"<[^>]+>")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fetch_json(url: str, timeout: float) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MKM-compression-public-corpus/1.0 (+research-only)"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _fetch_bytes(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MKM-compression-public-corpus/1.0 (+research-only)"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _strip_html(text: str) -> str:
    return TAG_RE.sub(" ", text or "").strip()


def _compose_text(*, source: str, title: str, body: str | None = None) -> str:
    chunks = [f"[public_open source={source}]", title.strip()]
    if body:
        clean = _strip_html(body).strip()
        if clean and clean.lower() != title.strip().lower():
            chunks.append(clean[:800])
    text = " ".join(chunks)
    return text[:2000]


def _base_row(
    *,
    row_id: str,
    source: str,
    domain_tag: str,
    text: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": row_id,
        "source": source,
        "domain_tag": domain_tag,
        "text": text,
        "public_open": True,
        "forbidden_as_customer_sla": True,
        "research_only": True,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "labels": ["DRAFT", "HYPO", "public_open_web", "not_customer_corpus"],
    }
    if extra:
        row.update(extra)
    return row


def fetch_hn(*, max_items: int, timeout: float, errors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        ids = _fetch_json(HN_TOP, timeout)
        if not isinstance(ids, list):
            raise ValueError("unexpected HN topstories shape")
        for hid in ids[: max_items * 2]:
            if len(rows) >= max_items:
                break
            try:
                item = _fetch_json(HN_ITEM.format(id=int(hid)), timeout)
            except (urllib.error.URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"hn_item_{hid}: {exc}")
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            text = _compose_text(source="hn_firebase_api", title=title)
            rows.append(
                _base_row(
                    row_id=f"public-hn-{len(rows):03d}",
                    source="hn_firebase_api_v1",
                    domain_tag="open-web-tech-news",
                    text=text,
                    extra={"hn_id": item.get("id"), "hn_url": item.get("url"), "hn_score": item.get("score")},
                )
            )
    except (urllib.error.URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"hn_topstories: {exc}")
    return rows


def fetch_wikipedia(*, max_items: int, timeout: float, errors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for topic in WIKI_TOPICS:
        if len(rows) >= max_items:
            break
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
        try:
            doc = _fetch_json(url, timeout)
        except (urllib.error.URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"wiki_{topic}: {exc}")
            continue
        title = str(doc.get("title") or topic).strip()
        extract = str(doc.get("extract") or "").strip()
        if not extract:
            continue
        text = _compose_text(source="wikipedia_rest", title=title, body=extract)
        rows.append(
            _base_row(
                row_id=f"public-wiki-{len(rows):03d}",
                source="wikipedia_rest_v1",
                domain_tag="open-web-encyclopedia",
                text=text,
                extra={"wiki_title": title, "content_urls": doc.get("content_urls")},
            )
        )
    return rows


def fetch_arxiv_rss(*, max_items: int, timeout: float, errors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        raw = _fetch_bytes(ARXIV_CS_AI_RSS, timeout)
        items = parse_feed_items(raw)
        for it in items:
            if len(rows) >= max_items:
                break
            title = str(it.get("title") or "").strip()
            if not title:
                continue
            desc = str(it.get("description") or "").strip()
            text = _compose_text(source="arxiv_cs_ai_rss", title=title, body=desc)
            rows.append(
                _base_row(
                    row_id=f"public-arxiv-{len(rows):03d}",
                    source="arxiv_cs_ai_rss_v1",
                    domain_tag="open-web-research-feed",
                    text=text,
                    extra={"link": it.get("link"), "published_utc": it.get("published_utc")},
                )
            )
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        errors.append(f"arxiv_rss: {exc}")
    return rows


def build_corpus(*, max_cases: int, timeout: float) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
    errors: list[str] = []
    per_source = max(8, max_cases // 3 + 1)
    hn = fetch_hn(max_items=per_source, timeout=timeout, errors=errors)
    wiki = fetch_wikipedia(max_items=per_source, timeout=timeout, errors=errors)
    arxiv = fetch_arxiv_rss(max_items=per_source, timeout=timeout, errors=errors)

    merged: list[dict[str, Any]] = []
    pools = [hn, wiki, arxiv]
    fetched_stats = {"hn": len(hn), "wikipedia": len(wiki), "arxiv_rss": len(arxiv)}
    idx = 0
    while len(merged) < max_cases and any(pools):
        pool = pools[idx % len(pools)]
        idx += 1
        if not pool:
            continue
        merged.append(pool.pop(0))

    stats = {**fetched_stats, "merged": len(merged)}
    return merged, errors, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument("--min-cases", type=int, default=20)
    ap.add_argument("--timeout-sec", type=float, default=25.0)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--dry-run", action="store_true", help="Fetch only; do not write files.")
    args = ap.parse_args()

    rows, errors, stats = build_corpus(max_cases=args.max_cases, timeout=args.timeout_sec)
    ok = len(rows) >= args.min_cases

    summary = {
        "ok": ok,
        "case_count": len(rows),
        "min_cases": args.min_cases,
        "source_stats": stats,
        "errors": errors,
        "out_jsonl": args.out_jsonl.resolve().relative_to(ROOT).as_posix() if ok else None,
    }
    print(json.dumps(summary, ensure_ascii=False))

    if args.dry_run:
        return 0 if ok else 1

    if not ok:
        return 1

    out = args.out_jsonl.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    manifest = {
        "schema": "compression_public_open_corpus_fetch_v1",
        "generated_at_utc": _utc(),
        "corpus_path": out.relative_to(ROOT).as_posix(),
        "case_count": len(rows),
        "sources": ["hn_firebase_api_v1", "wikipedia_rest_v1", "arxiv_cs_ai_rss_v1"],
        "source_stats": stats,
        "fetch_errors": errors,
        "labels": ["DRAFT", "research_only", "public_open_web", "not_customer_corpus"],
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "boundary_ack": (
            "Public API/RSS only — not customer masked JSONL; "
            "forbidden as customer case study or SEND_GATE OPEN headline."
        ),
    }
    man_path = args.manifest_json.resolve()
    man_path.parent.mkdir(parents=True, exist_ok=True)
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
