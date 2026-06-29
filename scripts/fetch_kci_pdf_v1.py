#!/usr/bin/env python3
"""Best-effort fetch KCI article PDF to docs/research/raw/ (no auth bypass)."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_html(arti_id: str) -> tuple[str, str]:
    urls = [
        (
            "view",
            "https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?"
            f"sereArticleSearchBean.artiId={arti_id}",
        ),
        (
            "landing",
            f"https://www.kci.go.kr/kciportal/landing/article.kci?arti_id={arti_id}",
        ),
    ]
    for label, url in urls:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MKM)", "Referer": "https://www.kci.go.kr/"})
        html = urllib.request.urlopen(req, timeout=35).read().decode("utf-8", "replace")
        if html:
            return html, label
    return "", "none"


def build_direct_urls(arti_id: str) -> list[str]:
    return [
        f"https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiFileDn.kci?sereArticleSearchBean.artiId={arti_id}",
        f"https://www.kci.go.kr/kciportal/po/search/poCopyrightPdfView.kci?sereArticleSearchBean.artiId={arti_id}",
    ]


def find_pdf_urls(html: str) -> list[str]:
    urls: list[str] = []
    priority: list[str] = []
    for m in re.finditer(r"poCopyrightPdfView\.kci\?[^\"'\s<>]+", html):
        u = "https://www.kci.go.kr/kciportal/po/search/" + m.group(0)
        priority.append(u)
    for m in re.finditer(r'sereId=(\d+)', html):
        u = f"https://www.kci.go.kr/kciportal/po/search/poCopyrightPdfView.kci?sereId={m.group(1)}"
        if u not in priority:
            priority.append(u)
    for m in re.finditer(r'https?://[^"\'\s<>]+\.pdf[^"\'\s<>]*', html, re.I):
        u = m.group(0)
        if "kci_data_filed" in u:
            continue
        if u not in urls:
            urls.append(u)
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
        href = m.group(1)
        if "kci_data_filed" in href:
            continue
        if "pdf" in href.lower() or "copyrightpdf" in href.lower():
            if href.startswith("/"):
                href = "https://www.kci.go.kr" + href
            if href.startswith("http") and href not in priority and href not in urls:
                urls.append(href)
    for u in urls:
        if u not in priority:
            priority.append(u)
    return priority[:10]


def pdf_looks_like_article(data: bytes, arti_id: str) -> bool:
    if not data[:5].startswith(b"%PDF") or len(data) < 20_000:
        return False
    try:
        import tempfile

        from pdfminer.high_level import extract_text

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            text = extract_text(tmp.name) or ""
    except Exception:
        return len(data) > 80_000
    needles = ("Kim", "김남일", "醫書", "日帝", "의사학", arti_id.replace("ART", ""))
    return sum(1 for n in needles if n in text) >= 2


def download(url: str, dest: Path, arti_id: str) -> bool:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (MKM)",
            "Referer": "https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=" + arti_id,
        },
    )
    data = urllib.request.urlopen(req, timeout=60).read()
    if not pdf_looks_like_article(data, arti_id):
        return False
    dest.write_bytes(data)
    return True


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--arti-id", required=True, help="e.g. ART001014143")
    ap.add_argument("--slug", default="", help="filename slug")
    args = ap.parse_args()

    arti_id = args.arti_id if args.arti_id.startswith("ART") else f"ART{args.arti_id}"
    slug = args.slug or arti_id
    view_url = (
        "https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?"
        f"sereArticleSearchBean.artiId={arti_id}"
    )

    log: dict[str, object] = {
        "schema": "fetch_kci_pdf_v1",
        "generated_at_utc": _utc(),
        "arti_id": arti_id,
        "view_url": view_url,
        "downloaded": False,
    }

    try:
        html, html_source = fetch_html(arti_id)
        log["html_source"] = html_source
    except OSError as exc:
        log["error"] = str(exc)
        out = ROOT / "reports/constitution/btrack_pilot" / f"{slug}_kci_fetch_v1.json"
        out.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(log, ensure_ascii=False))
        return 1

    pdf_urls = build_direct_urls(arti_id) + find_pdf_urls(html)
    log["pdf_url_candidates"] = pdf_urls
    log["has_闡幽_in_html"] = "闡幽" in html
    log["has_천유초_in_html"] = "천유초" in html

    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / f"{slug}_kci.pdf"

    for url in pdf_urls:
        try:
            if download(url, dest, arti_id):
                log["downloaded"] = True
                log["pdf_path"] = str(dest.relative_to(ROOT)).replace("\\", "/")
                log["pdf_url_used"] = url
                break
        except OSError as exc:
            log.setdefault("download_errors", []).append({"url": url, "error": str(exc)})

    if not log.get("downloaded"):
        log["note"] = "No public PDF link; use institutional KCI login or DBpia"
    elif dest.is_file():
        dest.unlink(missing_ok=True)
        log["downloaded"] = False
        log["note"] = "Rejected non-article PDF or auth HTML"

    out = ROOT / "reports/constitution/btrack_pilot" / f"{slug}_kci_fetch_v1.json"
    out.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": bool(log.get("downloaded")), **{k: log[k] for k in log if k != "pdf_url_candidates"}}, ensure_ascii=False))
    return 0 if log.get("downloaded") else 2


if __name__ == "__main__":
    raise SystemExit(main())
