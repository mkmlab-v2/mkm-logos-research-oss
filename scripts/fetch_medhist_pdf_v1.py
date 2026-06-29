#!/usr/bin/env python3
"""Fetch open PDF from medhist.or.kr (Korean J Med Hist) by article number."""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def guess_pdf_url(number: int, vol: int | None = None, issue: int | None = None, page: int | None = None) -> list[str]:
    cands: list[str] = []
    if vol and issue and page:
        cands.append(f"https://www.medhist.or.kr/upload/pdf/kjmh-{vol}-{issue}-{page}.pdf")
    cands.append(f"https://www.medhist.or.kr/upload/pdf/kjmh-{number}.pdf")
    return cands


def fetch_view(number: int) -> str:
    url = f"https://www.medhist.or.kr/journal/view.php?number={number}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MKM)"})
    return urllib.request.urlopen(req, timeout=35).read().decode("utf-8", "replace")


def extract_meta(html: str) -> dict:
    vol_issue = re.search(r"Volume\s+(\d+)\((\d+)\)", html)
    pages = re.search(r":\s*(\d+)-(\d+)", html)
    pdf_links = re.findall(r"/upload/pdf/[^\"'\s>]+\.pdf", html)
    return {
        "vol": int(vol_issue.group(1)) if vol_issue else None,
        "issue": int(vol_issue.group(2)) if vol_issue else None,
        "page_start": int(pages.group(1)) if pages else None,
        "pdf_links_in_html": ["https://www.medhist.or.kr" + p if p.startswith("/") else p for p in pdf_links],
    }


def download(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MKM)", "Referer": "https://www.medhist.or.kr/"})
    data = urllib.request.urlopen(req, timeout=60).read()
    if len(data) < 5000 or not data[:5].startswith(b"%PDF"):
        return False
    dest.write_bytes(data)
    return True


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--number", type=int, required=True, help="medhist article number e.g. 2131")
    ap.add_argument("--slug", default="", help="output filename slug")
    args = ap.parse_args()

    slug = args.slug or f"MEDHIST_{args.number}"
    dest = RAW / f"{slug}_medhist.pdf"
    log: dict[str, object] = {
        "schema": "fetch_medhist_pdf_v1",
        "generated_at_utc": _utc(),
        "article_number": args.number,
        "view_url": f"https://www.medhist.or.kr/journal/view.php?number={args.number}",
        "downloaded": False,
    }

    try:
        html = fetch_view(args.number)
        meta = extract_meta(html)
        log["meta"] = meta
    except OSError as exc:
        log["error"] = str(exc)
        _write_log(slug, log)
        print(json.dumps(log, ensure_ascii=False))
        return 1

    urls = list(meta.get("pdf_links_in_html") or [])
    urls.extend(
        guess_pdf_url(
            args.number,
            meta.get("vol"),
            meta.get("issue"),
            meta.get("page_start"),
        )
    )
    log["url_candidates"] = urls

    RAW.mkdir(parents=True, exist_ok=True)
    for url in urls:
        try:
            if download(url, dest):
                log["downloaded"] = True
                log["pdf_path"] = str(dest.relative_to(ROOT)).replace("\\", "/")
                log["pdf_url_used"] = url
                break
        except OSError as exc:
            log.setdefault("errors", []).append({"url": url, "error": str(exc)})

    if not log.get("downloaded"):
        log["note"] = "PDF URL guess failed; check medhist view page"

    _write_log(slug, log)
    print(json.dumps({"ok": bool(log.get("downloaded")), "pdf_path": log.get("pdf_path")}, ensure_ascii=False))
    return 0 if log.get("downloaded") else 2


def _write_log(slug: str, log: dict) -> None:
    out = ROOT / "reports/constitution/btrack_pilot" / f"{slug}_medhist_fetch_v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
