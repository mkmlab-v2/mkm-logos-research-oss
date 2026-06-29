#!/usr/bin/env python3
"""Probe KCI landing + view pages for PDF download URLs."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (MKM)",
            "Referer": "https://www.kci.go.kr/",
        },
    )
    return urllib.request.urlopen(req, timeout=35).read().decode("utf-8", "replace")


def extract_pdf_candidates(html: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r'(?:href|src|url)\s*[=:]\s*["\']([^"\']+)["\']', html, re.I):
        u = m.group(1)
        if any(k in u.lower() for k in ("pdf", "filedn", "copyrightpdf", "fulltext", "download")):
            if u.startswith("/"):
                u = "https://www.kci.go.kr" + u
            if u.startswith("http") and u not in out:
                out.append(u)
    for m in re.finditer(r"https?://[^\"'\s<>]+", html):
        u = m.group(0)
        if any(k in u.lower() for k in ("pdf", "filedn", "copyrightpdf")) and u not in out:
            out.append(u)
    return out


def main() -> int:
    arti = "ART001014143"
    pages = [
        f"https://www.kci.go.kr/kciportal/landing/article.kci?arti_id={arti}",
        f"https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId={arti}",
        f"https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiFileDn.kci?sereArticleSearchBean.artiId={arti}",
    ]
    doc = {"arti_id": arti, "pages": {}}
    for url in pages:
        try:
            html = fetch(url)
            doc["pages"][url] = {
                "len": len(html),
                "is_pdf": html[:5].startswith("%PDF") if len(html) > 5 else False,
                "candidates": extract_pdf_candidates(html)[:15],
                "has_cc": "크리에이티브 커먼즈" in html or "Creative Commons" in html,
            }
        except OSError as exc:
            doc["pages"][url] = {"error": str(exc)}

    out = ROOT / "reports/constitution/btrack_pilot/kci_ART001014143_pdf_probe_v1.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
