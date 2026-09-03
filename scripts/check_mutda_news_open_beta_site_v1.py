#!/usr/bin/env python3
"""Deterministic check for MUTDA OPEN_BETA Visual Baseline v1.

This validates structure/copy boundaries only. It does not establish semantic
quality, PRODUCT_DONE, market fit, or deploy authorization.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "projects/mutda-news-open-beta-v1/public"
DESIGN_SSOT = ROOT / "projects/mutda-news-open-beta-v1/MUTDA_DESIGN_SSOT_V1.md"

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

FORBIDDEN_PUBLIC = [
    re.compile(r"편향\s*없는\s*뉴스"),
    re.compile(r"완치"),
    re.compile(r"처방합니다"),
    re.compile(r"진단합니다"),
    re.compile(r"부작용\s*없음"),
    re.compile(r"무조건\s*효과"),
    re.compile(r"완성\s*성경\s*AI"),
    re.compile(r"PRODUCT_DONE", re.I),
    re.compile(r"FRIEND_READY", re.I),
    re.compile(r"\bNON_GATING\b", re.I),
    re.compile(r"Final\s+Action", re.I),
    re.compile(r"research\s+assist", re.I),
    re.compile(r"secondary\s*/\s*footer", re.I),
    re.compile(r"news_role\s*="),
    re.compile(r"provenance\s*="),
    re.compile(r"mkm_mutda_series_ep01_v1_latest\.json"),
    re.compile(r"docs/final/artifacts/"),
    re.compile(r"Ask\s*시드"),
    re.compile(r"MUDDA"),
    re.compile(r"怖い"),
]

RAW_EP01_MARKDOWN = [
    re.compile(r"(?m)^\s*#{3,4}\s+"),
    re.compile(r"\*\*[^*\n]+\*\*"),
]


def must_contain(errors: list[str], rel: str, needles: list[str]) -> None:
    path = PUBLIC / rel
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            errors.append(f"{rel} missing required public copy: {needle}")


def main() -> int:
    errors: list[str] = []

    if not DESIGN_SSOT.is_file():
        errors.append("missing MUTDA_DESIGN_SSOT_V1.md")
    if not PUBLIC.is_dir():
        print(f"FAIL missing public dir: {PUBLIC}")
        return 2

    for rel in REQUIRED:
        if not (PUBLIC / rel).is_file():
            errors.append(f"missing: {rel}")

    must_contain(errors, "index.html", ["무엇을 묻고 싶으세요?", "뉴스 묻다", "성경 묻다", "Beta"])
    must_contain(errors, "news/index.html", ["먼저 무엇이 사실인지 묻습니다", "EP01"])
    must_contain(errors, "news/ep01/index.html", ["사실", "왜", "다른 관점", "그래서 무엇을 볼까", "의료 진단·처방·치료를 대체하지 않으며"])
    must_contain(errors, "bible/index.html", ["성경 묻다", "본문", "문맥", "해석", "다른 관점", "근거", "더 묻기"])
    must_contain(errors, "ask/index.html", ["이 질문을 조금 더 이어가 볼까요?", "jema-ai.com/ask"])
    must_contain(errors, "about/index.html", ["주식회사 목소리네트워크", "MKM LAB", "Beta 원칙"])

    ep01 = PUBLIC / "news/ep01/index.html"
    if ep01.is_file():
        ep01_text = ep01.read_text(encoding="utf-8")
        for pattern in RAW_EP01_MARKDOWN:
            if pattern.search(ep01_text):
                errors.append(f"EP01 leaked raw markdown token: {pattern.pattern}")

    scan_ext = {".html", ".txt", ".xml", ".css"}
    for path in PUBLIC.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in scan_ext:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(PUBLIC).as_posix()
        for pattern in FORBIDDEN_PUBLIC:
            if pattern.search(content):
                errors.append(f"forbidden public token '{pattern.pattern}' in {rel}")

    manifest = PUBLIC / "build_manifest.json"
    if manifest.is_file():
        mt = manifest.read_text(encoding="utf-8")
        if '"visual_baseline": "MUTDA_DESIGN_SSOT_V1"' not in mt:
            errors.append("build manifest missing visual baseline id")
        if '"PRODUCT_DONE": false' not in mt:
            errors.append("build manifest must retain PRODUCT_DONE=false internally")
        if '"logos_research_workspace_keep": true' not in mt:
            errors.append("build manifest must retain Logos KEEP boundary")

    if errors:
        print("FAIL check_mutda_news_open_beta_site_v1")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("OK check_mutda_news_open_beta_site_v1")
    print("  visual_baseline=MUTDA_DESIGN_SSOT_V1")
    print(f"  required_files={len(REQUIRED)}")
    print("  ep01_markdown_leak_guard=ON")
    print("  evidence_ceiling=STRUCTURAL_PRESENTATION_CHECK_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
