#!/usr/bin/env python3
"""Verify a-codeai static HTML templates follow Google subdirectory i18n (EN default)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "scripts" / "deploy" / "nginx"
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_codeai_i18n_routes_v1_latest.json"
BASE = "https://a-codeai.com"

PAGE_ROUTES: list[dict[str, str]] = [
    {
        "page_id": "home",
        "en_template": "a-codeai.com.index.en.html.example",
        "ko_template": "a-codeai.com.index.html.example",
        "en_url": f"{BASE}/",
        "ko_url": f"{BASE}/ko/",
    },
    {
        "page_id": "pilot",
        "en_template": "a-codeai.com.pilot.en.html.example",
        "ko_template": "a-codeai.com.pilot.html.example",
        "en_url": f"{BASE}/pilot/",
        "ko_url": f"{BASE}/ko/pilot/",
    },
    {
        "page_id": "benchmark",
        "en_template": "a-codeai.com.benchmark.en.html.example",
        "ko_template": "a-codeai.com.benchmark.html.example",
        "en_url": f"{BASE}/benchmark/",
        "ko_url": f"{BASE}/ko/benchmark/",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _has_hreflang(text: str, lang: str, href: str) -> bool:
    pattern = rf'<link[^>]+rel=["\']alternate["\'][^>]+hreflang=["\']{re.escape(lang)}["\'][^>]+href=["\']{re.escape(href)}["\']'
    pattern_rev = rf'<link[^>]+hreflang=["\']{re.escape(lang)}["\'][^>]+href=["\']{re.escape(href)}["\']'
    return bool(re.search(pattern, text, flags=re.I)) or bool(re.search(pattern_rev, text, flags=re.I))


def _has_canonical(text: str, href: str) -> bool:
    pattern = rf'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']{re.escape(href)}["\']'
    pattern_rev = rf'<link[^>]+href=["\']{re.escape(href)}["\'][^>]+rel=["\']canonical["\']'
    return bool(re.search(pattern, text, flags=re.I)) or bool(re.search(pattern_rev, text, flags=re.I))


def _check_locale_file(
    *,
    path: Path,
    lang: str,
    canonical: str,
    en_url: str,
    ko_url: str,
    x_default: str,
) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    html_lang = re.search(r"<html[^>]+lang=[\"']([^\"']+)[\"']", text, flags=re.I)
    checks = {
        "html_lang_ok": bool(html_lang and html_lang.group(1).lower() == lang),
        "canonical_ok": _has_canonical(text, canonical),
        "hreflang_en_ok": _has_hreflang(text, "en", en_url),
        "hreflang_ko_ok": _has_hreflang(text, "ko", ko_url),
        "hreflang_x_default_ok": _has_hreflang(text, "x-default", x_default),
        "lang_switcher_ok": (
            ('href="/"' in text or 'href="/pilot"' in text or 'href="/benchmark"' in text)
            if lang == "ko"
            else ("/ko/" in text or 'href="/ko' in text)
        ),
    }
    checks["ok"] = all(checks.values())
    return checks


def build_report() -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    all_ok = True
    for route in PAGE_ROUTES:
        en_path = TEMPLATE_DIR / route["en_template"]
        ko_path = TEMPLATE_DIR / route["ko_template"]
        if not en_path.is_file() or not ko_path.is_file():
            all_ok = False
            pages.append(
                {
                    "page_id": route["page_id"],
                    "ok": False,
                    "reason": "missing_template",
                    "en_template": route["en_template"],
                    "ko_template": route["ko_template"],
                }
            )
            continue
        en_checks = _check_locale_file(
            path=en_path,
            lang="en",
            canonical=route["en_url"],
            en_url=route["en_url"],
            ko_url=route["ko_url"],
            x_default=route["en_url"],
        )
        ko_checks = _check_locale_file(
            path=ko_path,
            lang="ko",
            canonical=route["ko_url"],
            en_url=route["en_url"],
            ko_url=route["ko_url"],
            x_default=route["en_url"],
        )
        page_ok = bool(en_checks["ok"] and ko_checks["ok"])
        all_ok = all_ok and page_ok
        pages.append(
            {
                "page_id": route["page_id"],
                "ok": page_ok,
                "default_locale": "en",
                "routing_model": "subdirectory",
                "en_url": route["en_url"],
                "ko_url": route["ko_url"],
                "en_template": route["en_template"],
                "ko_template": route["ko_template"],
                "checks": {"en": en_checks, "ko": ko_checks},
            }
        )
    return {
        "schema": "a_codeai_i18n_routes_v1",
        "generated_at_utc": _utc_now(),
        "policy": {
            "default_locale": "en",
            "secondary_locale": "ko",
            "x_default_points_to": "en",
            "google_pattern": "subdirectory_hreflang_canonical",
            "deploy_ssot": "scripts/deploy/linux/deploy_a_codeai_landing_from_repo.sh",
        },
        "all_ok": all_ok,
        "pages": pages,
        "reproduce": "py scripts/check_a_codeai_i18n_templates_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 when all_ok is false.")
    args = ap.parse_args()

    report = build_report()
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "all_ok": report["all_ok"], "out": str(out_path)}, ensure_ascii=False))
    if args.strict and not report["all_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
