#!/usr/bin/env python3
"""Local check for MUTDA News OPEN_BETA static site.

- Required file existence under projects/mutda-news-open-beta-v1/public/
- Forbidden copy regex (overclaim / medical overreach / mock leftovers)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "projects" / "mutda-news-open-beta-v1" / "public"

REQUIRED = [
    "index.html",
    "news/index.html",
    "news/ep01/index.html",
    "bible/index.html",
    "ask/index.html",
    "about/index.html",
    "robots.txt",
    "sitemap.xml",
    "assets/site.css",
    "assets/bible_ask_stub_v1.js",
]

# Overclaim / medical / mock leftovers — must not appear in public HTML/txt/xml/css
FORBIDDEN = [
    re.compile(r"편향\s*없는\s*뉴스"),
    re.compile(r"역대\s*최저"),
    re.compile(r"완치"),
    re.compile(r"처방합니다"),
    re.compile(r"진단합니다"),
    re.compile(r"부작용\s*없음"),
    re.compile(r"무조건\s*효과"),
    re.compile(r"완성\s*성경\s*AI"),
    re.compile(r"PRODUCT_DONE\s*=\s*true", re.I),
    re.compile(r"product\s+DONE", re.I),
    re.compile(r"FRIEND_READY\s*=\s*true", re.I),
    re.compile(r"research_only"),
    re.compile(r"\bPREP\b"),
    re.compile(r"SEND\s+HOLD"),
]


def main() -> int:
    errors: list[str] = []
    if not PUBLIC.is_dir():
        print(f"FAIL missing public dir: {PUBLIC}")
        return 2

    for rel in REQUIRED:
        path = PUBLIC / rel
        if not path.is_file():
            errors.append(f"missing: {rel}")

    # EP01 must carry disclaimer + provenance + NON_GATING lens note
    ep = PUBLIC / "news" / "ep01" / "index.html"
    if ep.is_file():
        text = ep.read_text(encoding="utf-8")
        for needle in (
            "disclaimer",
            "mkm_mutda_series_ep01_v1_latest.json",
            "[NON_GATING]",
            "OPEN_BETA",
        ):
            if needle not in text and needle.lower() not in text.lower():
                # disclaimer may be Korean block; check Korean phrase from sealed pack
                pass
        if "NON_GATING" not in text:
            errors.append("ep01 missing [NON_GATING] lens note")
        if "mkm_mutda_series_ep01_v1_latest.json" not in text:
            errors.append("ep01 missing provenance path")
        if "의료 진단·처방·치료를 대체하지 않으며" not in text:
            errors.append("ep01 missing disclaimer_ko verbatim fragment")
        if "FACT" not in text or "CAUSE" not in text or "LENS" not in text or "DECISION" not in text:
            errors.append("ep01 missing FACT/CAUSE/LENS/DECISION structure")

    home = PUBLIC / "index.html"
    if home.is_file():
        ht = home.read_text(encoding="utf-8")
        if "사실을 나누고 판단을 돕는 AI" not in ht:
            errors.append("home missing tagline")
        if "OPEN_BETA" not in ht:
            errors.append("home missing OPEN_BETA badge")
        if "og:title" not in ht:
            errors.append("home missing OG tags")
        if "/bible/" not in ht or "성경 묻다 — Beta" not in ht:
            errors.append("home missing bible Beta hub CTA")

    bible = PUBLIC / "bible" / "index.html"
    if bible.is_file():
        bt = bible.read_text(encoding="utf-8")
        if "성경 묻다 — Beta" not in bt:
            errors.append("bible page missing Beta title copy")
        for slot in ("본문", "문맥", "해석", "다른 관점", "근거"):
            if slot not in bt:
                errors.append(f"bible page missing slot label: {slot}")
        if "더 묻기" not in bt:
            errors.append("bible page missing 더 묻기 control")
        if "logos.jema-ai.com" not in bt:
            errors.append("bible page must keep logos.jema-ai.com link")
        if "완성 성경 AI" in bt:
            errors.append("bible page forbids 완성 성경 AI copy")

    ask = PUBLIC / "ask" / "index.html"
    if ask.is_file():
        at = ask.read_text(encoding="utf-8")
        if "jema-ai.com/ask" not in at:
            errors.append("ask page must deep-link jema-ai.com/ask")
        if "mutda.ai에 호스팅" in at or "Ask는 mutda" in at:
            # positive: we want clarifying copy that Ask is NOT on mutda — OK if present
            pass

    about = PUBLIC / "about" / "index.html"
    if about.is_file():
        ab = about.read_text(encoding="utf-8")
        if "주식회사 목소리네트워크" not in ab:
            errors.append("about missing company name")
        if "MKM LAB" not in ab:
            errors.append("about missing MKM LAB secondary")

    scan_ext = {".html", ".txt", ".xml", ".css", ".json"}
    for path in PUBLIC.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in scan_ext:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(PUBLIC).as_posix()
        for pat in FORBIDDEN:
            if pat.search(content):
                errors.append(f"forbidden '{pat.pattern}' in {rel}")

    if errors:
        print("FAIL check_mutda_news_open_beta_site_v1")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("OK check_mutda_news_open_beta_site_v1")
    print(f"  public={PUBLIC.relative_to(ROOT).as_posix()}")
    print(f"  required_files={len(REQUIRED)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
