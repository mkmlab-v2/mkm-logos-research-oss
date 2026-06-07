#!/usr/bin/env python3
"""B-track rebuild: apocrypha Sefaria/URL collect → token NDJSON (ext2 weighted + ext3 hebrew).

Replaces missing 2026-03-27 local-only frontline scripts. Metadata-only token rows
(no raw scroll text in MKM ingest). research_only · [HYPO] · not Track A.

Usage (from repo root):
  py projects/dss-4d-ingest/run_apocrypha_pilot.py --manifest pilot_manifest_ext2.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

USER_AGENT = "MKM-DssApocryphaRebuild/1.0 (+research_only)"


def _http_get(url: str, *, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _http_get_json(url: str, *, timeout: int = 45, retries: int = 3) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return json.loads(_http_get(url, timeout=timeout))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            last = e
            if attempt >= retries:
                break
            time.sleep(0.5 * (2**attempt) + random.random() * 0.1)
    assert last is not None
    raise last


def _chapter_count(index: dict[str, Any]) -> int:
    for key in ("lengths",):
        val = index.get(key)
        if isinstance(val, list) and val:
            return int(val[0])
    schema = index.get("schema")
    if isinstance(schema, dict):
        sl = schema.get("lengths")
        if isinstance(sl, list) and sl:
            return int(sl[0])
    raise ValueError("no chapter count in index")


def _normalize_cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return " ".join(x for x in (_normalize_cell(i) for i in v) if x).strip()
    return str(v).strip()


def _is_hebrew(text: str) -> bool:
    return bool(re.search(r"[\u0590-\u05FF]", text))


def _tokenize(text: str) -> list[str]:
    text = re.sub(r"<[^>]+>", " ", text)
    parts = re.split(r"[\s\u00a0]+", text)
    out: list[str] = []
    for p in parts:
        t = re.sub(r"^[^\w\u0590-\u05FF]+|[^\w\u0590-\u05FF]+$", "", p)
        if len(t) >= 2:
            out.append(t)
    return out


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "nav"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav"):
            self._skip = False
        if tag in ("p", "br", "div", "h1", "h2", "h3", "li"):
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._chunks.append(data)

    def text(self) -> str:
        return "".join(self._chunks)


def _fetch_sefaria_work(work_id: str, slug: str, *, max_chapters: int | None, delay: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    idx = _http_get_json(f"https://www.sefaria.org/api/v2/index/{urllib.parse.quote(slug)}")
    n_ch = _chapter_count(idx)
    if max_chapters is not None:
        n_ch = min(n_ch, max_chapters)
    for ch in range(1, n_ch + 1):
        time.sleep(delay)
        ref = f"{slug}.{ch}"
        data = _http_get_json(
            f"https://www.sefaria.org/api/texts/{urllib.parse.quote(ref)}?context=0"
        )
        he_list = data.get("he") if isinstance(data.get("he"), list) else []
        en_list = data.get("text") if isinstance(data.get("text"), list) else []
        n = max(len(he_list), len(en_list))
        for vi in range(n):
            he = _normalize_cell(he_list[vi] if vi < len(he_list) else "")
            en = _normalize_cell(en_list[vi] if vi < len(en_list) else "")
            body = he if he else en
            if not body:
                continue
            rows.append(
                {
                    "work_id": work_id,
                    "ref": f"{slug}.{ch}.{vi + 1}",
                    "text": body,
                    "lang": "he" if he else "en",
                    "source": "SEFARIA_API",
                }
            )
    return rows


def _fetch_url_work(work_id: str, url: str, *, max_pages: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    html = _http_get(url)
    parser = _TextExtractor()
    parser.feed(html)
    text = parser.text()
    # sacred-texts index: follow first N chapter links
    links = re.findall(r'href="([^"]+\.htm)"', html, flags=re.I)
    chapter_links: list[str] = []
    base = url.rsplit("/", 1)[0] + "/"
    for href in links:
        if href.startswith("http"):
            full = href
        else:
            full = urllib.parse.urljoin(base, href)
        if "boe" in full.lower() and full != url and full not in chapter_links:
            chapter_links.append(full)
        if len(chapter_links) >= max_pages:
            break
    if not chapter_links:
        for para in re.split(r"\n{2,}", text):
            p = para.strip()
            if len(p) > 80:
                rows.append(
                    {
                        "work_id": work_id,
                        "ref": url,
                        "text": p[:4000],
                        "lang": "en",
                        "source": "URL_TEXT",
                    }
                )
        return rows
    for i, link in enumerate(chapter_links, start=1):
        time.sleep(0.35)
        try:
            ch_html = _http_get(link)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            continue
        p = _TextExtractor()
        p.feed(ch_html)
        body = p.text().strip()
        if len(body) < 40:
            continue
        rows.append(
            {
                "work_id": work_id,
                "ref": link,
                "text": body[:8000],
                "lang": "en",
                "source": "URL_TEXT",
            }
        )
    return rows


def _dedupe_raw(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = hashlib.sha256(
            f"{row['work_id']}|{row.get('ref')}|{row['text'][:200]}".encode("utf-8")
        ).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _raw_to_tokens(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    per_work: Counter[str] = Counter()
    for row in raw_rows:
        work = str(row["work_id"])
        lang = str(row.get("lang") or "en")
        script = "hebrew" if lang == "he" or _is_hebrew(str(row.get("text") or "")) else "other"
        tier = "A_HEBREW_PRIMARY" if script == "hebrew" else "C_TRANSLATION_PROXY"
        for _tok in _tokenize(str(row.get("text") or "")):
            per_work[work] += 1
            tokens.append(
                {
                    "work": work,
                    "token_index": per_work[work],
                    "script": script,
                    "lineage_tier": tier,
                    "source": str(row.get("source") or "UNKNOWN"),
                    "lang": lang,
                    "ref": row.get("ref"),
                }
            )
    return tokens


def _annotate_weighted(tokens: list[dict[str, Any]], *, canon_weight: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in tokens:
        row = dict(t)
        if row.get("lineage_tier") == "A_HEBREW_PRIMARY":
            row["effective_weight"] = canon_weight
        else:
            row["effective_weight"] = round(canon_weight * 0.33, 6)
        out.append(row)
    return out


def _quality_report(tokens: list[dict[str, Any]]) -> dict[str, Any]:
    works: Counter[str] = Counter()
    tiers: Counter[str] = Counter()
    scripts: Counter[str] = Counter()
    langs: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    for t in tokens:
        works[str(t.get("work"))] += 1
        tiers[str(t.get("lineage_tier"))] += 1
        scripts[str(t.get("script"))] += 1
        langs[str(t.get("lang"))] += 1
        sources[str(t.get("source"))] += 1
    hebrew_primary = tiers.get("A_HEBREW_PRIMARY", 0)
    translation = tiers.get("C_TRANSLATION_PROXY", 0)
    total = len(tokens)
    return {
        "total_tokens": total,
        "lineage_tier_counts": dict(tiers),
        "script_counts": dict(scripts),
        "work_counts": dict(works),
        "lang_counts": dict(langs),
        "source_counts": dict(sources),
        "hebrew_primary_tokens": hebrew_primary,
        "translation_proxy_ratio": round(translation / total, 6) if total else 0.0,
        "effective_weight_avg_by_tier": {
            "A_HEBREW_PRIMARY": 1.0,
            "C_TRANSLATION_PROXY": 0.33,
        },
    }


def _write_ndjson(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=str, default="pilot_manifest_ext2.json")
    ap.add_argument("--works-json", type=Path, default=root / "pilot_works_apocrypha_extended.json")
    ap.add_argument("--url-sources-json", type=Path, default=root / "pilot_url_sources_apocrypha.json")
    ap.add_argument("--output-dir", type=Path, default=root / "outputs")
    ap.add_argument("--max-chapters-per-work", type=int, default=None)
    ap.add_argument("--max-url-pages", type=int, default=40)
    ap.add_argument("--sefaria-delay", type=float, default=0.25)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    works_doc = json.loads(args.works_json.read_text(encoding="utf-8"))
    url_doc = json.loads(args.url_sources_json.read_text(encoding="utf-8")) if args.url_sources_json.is_file() else {"sources": []}

    raw_rows: list[dict[str, Any]] = []
    for w in works_doc.get("works") or []:
        if not isinstance(w, dict):
            continue
        work_id = str(w.get("work_id") or "")
        slug = str(w.get("sefaria_slug") or "")
        if not work_id or not slug:
            continue
        if args.dry_run:
            raw_rows.append(
                {
                    "work_id": work_id,
                    "ref": f"{slug}.1.1",
                    "text": "בְּרֵאשִׁית dry run token sample",
                    "lang": "he",
                    "source": "SEFARIA_API",
                }
            )
            continue
        raw_rows.extend(
            _fetch_sefaria_work(
                work_id,
                slug,
                max_chapters=args.max_chapters_per_work,
                delay=args.sefaria_delay,
            )
        )

    for src in url_doc.get("sources") or []:
        if not isinstance(src, dict):
            continue
        work_id = str(src.get("work_id") or "")
        url = str(src.get("url") or "")
        if not work_id or not url:
            continue
        if args.dry_run:
            raw_rows.append(
                {
                    "work_id": work_id,
                    "ref": url,
                    "text": "dry run enoch sample paragraph for tokenization",
                    "lang": "en",
                    "source": "URL_TEXT",
                }
            )
            continue
        raw_rows.extend(_fetch_url_work(work_id, url, max_pages=args.max_url_pages))

    deduped = _dedupe_raw(raw_rows)
    tokens = _raw_to_tokens(deduped)
    weighted = _annotate_weighted(tokens, canon_weight=1.0)
    hebrew_priority = [t for t in weighted if t.get("lineage_tier") == "A_HEBREW_PRIMARY"] or weighted

    out_ext2 = args.output_dir / "apocrypha_tokens_pilot_manifest_ext2_weighted.ndjson"
    out_ext3 = args.output_dir / "apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson"
    out_quality_ext2 = args.output_dir / "apocrypha_quality_report_pilot_manifest_ext2.json"
    out_quality_ext3 = args.output_dir / "apocrypha_quality_report_pilot_manifest_ext3_hebrew_priority.json"
    out_gate = args.output_dir / "apocrypha_gate_decision_pilot_manifest_ext2.json"

    _write_ndjson(out_ext2, weighted)
    _write_ndjson(out_ext3, hebrew_priority)
    q2 = _quality_report(weighted)
    q3 = _quality_report(hebrew_priority)
    out_quality_ext2.write_text(json.dumps(q2, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_quality_ext3.write_text(json.dumps(q3, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gate = {
        "decision": "PASS" if q2["total_tokens"] >= 100 else "WATCH",
        "total_tokens": q2["total_tokens"],
        "rebuild_lane": "B_track_apocrypha_rebuild_v1",
        "research_only": True,
    }
    out_gate.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {len(weighted)} weighted token records to {out_ext2}")
    print(f"wrote {len(hebrew_priority)} hebrew-priority records to {out_ext3}")
    print(f"OK: verified {len(weighted)} records")
    print(json.dumps({"ok": True, "ext2_records": len(weighted), "ext3_records": len(hebrew_priority)}, ensure_ascii=False))
    return 0 if weighted else 2


if __name__ == "__main__":
    raise SystemExit(main())
