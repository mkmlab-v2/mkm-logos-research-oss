#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Harvest Europe PMC metadata for Sasang-medicine papers that mention demographics / birth / age.

Purpose
-------
- **Bench / training prep:** build a deduped catalog (PMID, title, abstract snippet, query hit)
  for curators to triage. Full-text often needs library access; this CLI stays on the public REST API.

Limits (Fact-Lock honest)
-------------------------
- Abstracts **rarely** contain reproducible ``birth_instant_utc`` + IANA TZ + certified Sasang label
  for the **same identifiable person**. Treat hits as **literature leads**, not finished joint rows.
- Do not scrape identifiable participant tables from paywalled PDFs here. Merge those offline with
  ``data/myeongni/sasang_saju_joint_benchmark_v1.jsonl`` (schema in this module docstring).

Joint benchmark row schema (``sasang_saju_joint_benchmark_row_v1``)
-----------------------------------------------------------------
Minimal fields for human or cross-source merge::

    schema, person_id, benchmark_tier, privacy_tier, provenance,
    sasang_constitution: {label_ko, label_en, confidence, source:{pmid, quote}},
    birth_resolution: {birth_instant_utc, iana_tz, is_male} | null,
    literature_catalog_pmids: [str, ...]

Europe PMC: https://www.ebi.ac.uk/europepmc/webservices/rest/search
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "myeongni" / "sasang_saju_literature_catalog_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "data" / "myeongni" / "sasang_saju_literature_catalog_manifest_v1.json"
EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# Broad queries: Sasang / SCM + demographics; second pass narrows "birth" wording.
DEFAULT_QUERIES: tuple[str, ...] = (
    '("Sasang constitutional medicine" OR "Sasang medicine" OR "Sasang typology") '
    "AND (demographic OR participant OR patient OR cohort OR clinical)",
    '("Sasang constitutional medicine" OR "Sasang medicine") AND (age OR sex OR gender OR BMI)',
    '("Sasang constitutional medicine" OR "Sasang medicine") AND (birth OR birthday OR "date of birth" OR DOB)',
)


def _fetch_page(query: str, *, page: int, page_size: int, timeout_sec: float) -> dict[str, Any]:
    params = {
        "query": query,
        "format": "json",
        "page": str(page),
        "pageSize": str(page_size),
        "resultType": "core",
    }
    url = EPMC_SEARCH + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "mkm-workspace-fetch/1.0 (literature catalog)"})
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _normalize_hit(hit: dict[str, Any], *, query: str) -> dict[str, Any]:
    pmid = str(hit.get("pmid") or hit.get("id") or "").strip()
    title = str(hit.get("title") or "").strip()
    abstract = str(hit.get("abstractText") or "").strip()
    if len(abstract) > 1200:
        abstract = abstract[:1197] + "..."
    src = str(hit.get("source") or "").strip()
    journal = str(hit.get("journalTitle") or "").strip()
    year = hit.get("pubYear")
    return {
        "schema": "sasang_saju_literature_catalog_row_v1",
        "pmid": pmid,
        "source": src,
        "title": title,
        "journalTitle": journal,
        "pubYear": year,
        "abstractText": abstract,
        "authorString": str(hit.get("authorString") or "").strip(),
        "query_matched": query,
        "europepmc_url": f"https://europepmc.org/article/MED/{pmid}" if pmid.isdigit() else "",
    }


def fetch_catalog(
    *,
    queries: tuple[str, ...],
    max_total: int,
    page_size: int,
    sleep_sec: float,
    timeout_sec: float,
    fixture_path: Path | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return rows and manifest stats."""
    if fixture_path is not None:
        doc = json.loads(fixture_path.read_text(encoding="utf-8"))
        raw_hits = doc.get("resultList", {}).get("result") or []
        if not isinstance(raw_hits, list):
            raw_hits = []
        rows = [_normalize_hit(h, query="fixture") for h in raw_hits if isinstance(h, dict)]
        manifest = {
            "schema": "sasang_saju_literature_catalog_manifest_v1",
            "mode": "fixture",
            "fixture_path": str(fixture_path),
            "deduped_rows": len(rows),
        }
        return rows[:max_total], manifest

    seen: set[str] = set()
    out_rows: list[dict[str, Any]] = []
    errors: list[str] = []

    max_pages_per_query = 80

    for q in queries:
        page = 1
        while len(out_rows) < max_total and page <= max_pages_per_query:
            try:
                doc = _fetch_page(q, page=page, page_size=page_size, timeout_sec=timeout_sec)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
                errors.append(f"query={q!r} page={page}: {e}")
                break
            raw_hits = doc.get("resultList", {}).get("result") or []
            if not isinstance(raw_hits, list) or not raw_hits:
                break
            added = 0
            for h in raw_hits:
                if not isinstance(h, dict):
                    continue
                row = _normalize_hit(h, query=q)
                pmid = row.get("pmid") or ""
                key = f"{row.get('source')}:{pmid}" if pmid else json.dumps(row.get("title"), ensure_ascii=False)
                if key in seen:
                    continue
                seen.add(key)
                out_rows.append(row)
                added += 1
                if len(out_rows) >= max_total:
                    break
            page += 1
            if sleep_sec > 0:
                time.sleep(sleep_sec)
            if len(raw_hits) < page_size:
                break
            if added == 0:
                break

    manifest = {
        "schema": "sasang_saju_literature_catalog_manifest_v1",
        "mode": "live",
        "queries": list(queries),
        "max_total": max_total,
        "deduped_rows": len(out_rows),
        "errors": errors,
    }
    return out_rows, manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="JSONL catalog output path")
    ap.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="JSON manifest with run metadata",
    )
    ap.add_argument("--max-total", type=int, default=200, help="Stop after this many deduped rows")
    ap.add_argument("--page-size", type=int, default=50)
    ap.add_argument("--sleep-sec", type=float, default=0.35, help="Polite delay between pages")
    ap.add_argument("--timeout-sec", type=float, default=45.0)
    ap.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="If set, read this JSON instead of calling Europe PMC (tests / air-gapped)",
    )
    ap.add_argument(
        "--queries-file",
        type=Path,
        default=None,
        help="UTF-8 text file, one Europe PMC query per line (non-empty, non-#)",
    )
    args = ap.parse_args()

    queries: tuple[str, ...]
    if args.queries_file:
        lines = args.queries_file.read_text(encoding="utf-8").splitlines()
        queries = tuple(
            ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")
        )
        if not queries:
            print("No queries in --queries-file", file=sys.stderr)
            return 2
    else:
        queries = DEFAULT_QUERIES

    rows, manifest = fetch_catalog(
        queries=queries,
        max_total=max(1, int(args.max_total)),
        page_size=max(5, min(100, int(args.page_size))),
        sleep_sec=max(0.0, float(args.sleep_sec)),
        timeout_sec=float(args.timeout_sec),
        fixture_path=args.fixture,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest["out_path"] = str(args.out.resolve())
    manifest["generated_note"] = (
        "Rows are metadata only. Curate joint sasang+saju rows separately; see module docstring."
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"deduped_rows": len(rows), "out": str(args.out), "manifest": str(args.manifest)}, indent=2))
    return 0 if not manifest.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
