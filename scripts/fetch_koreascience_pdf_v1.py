#!/usr/bin/env python3
"""Fetch PDF from koreascience.or.kr JAKO article page if OA link exists."""

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


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--jako-id", required=True, help="e.g. JAKO201913661037959")
    ap.add_argument("--slug", required=True)
    args = ap.parse_args()

    page = f"https://koreascience.or.kr/article/{args.jako_id}.page"
    dest = RAW / f"{args.slug}_koreascience.pdf"
    log: dict = {
        "schema": "fetch_koreascience_pdf_v1",
        "generated_at_utc": _utc(),
        "jako_id": args.jako_id,
        "page_url": page,
        "downloaded": False,
    }

    try:
        req = urllib.request.Request(page, headers={"User-Agent": "Mozilla/5.0 (MKM)"})
        html = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
    except OSError as exc:
        log["error"] = str(exc)
        print(json.dumps(log, ensure_ascii=False))
        return 2

    pdf_urls = re.findall(r"https?://[^\"'\s>]+\.pdf", html)
    pdf_urls += [f"https://koreascience.or.kr{u}" for u in re.findall(r"/[^\"'\s>]+\.pdf", html)]
    log["pdf_candidates"] = list(dict.fromkeys(pdf_urls))[:10]

    for url in log["pdf_candidates"]:
        try:
            req2 = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MKM)", "Referer": page})
            data = urllib.request.urlopen(req2, timeout=60).read()
            if data[:4] == b"%PDF" and len(data) > 5000:
                dest.write_bytes(data)
                log["downloaded"] = True
                log["pdf_url"] = url
                log["dest"] = str(dest.relative_to(ROOT)).replace("\\", "/")
                print(json.dumps(log, ensure_ascii=False))
                return 0
        except OSError as exc:
            log.setdefault("errors", []).append({"url": url, "error": str(exc)[:120]})

    # try common koreascience PDF pattern
    alt = f"https://koreascience.or.kr/article/{args.jako_id}.pdf"
    try:
        req3 = urllib.request.Request(alt, headers={"User-Agent": "Mozilla/5.0 (MKM)", "Referer": page})
        data = urllib.request.urlopen(req3, timeout=60).read()
        if data[:4] == b"%PDF" and len(data) > 5000:
            dest.write_bytes(data)
            log["downloaded"] = True
            log["pdf_url"] = alt
            log["dest"] = str(dest.relative_to(ROOT)).replace("\\", "/")
            print(json.dumps(log, ensure_ascii=False))
            return 0
    except OSError as exc:
        log.setdefault("errors", []).append({"url": alt, "error": str(exc)[:120]})

    print(json.dumps(log, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
