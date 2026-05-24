#!/usr/bin/env python3
"""Build K-Startup majung (BMO0902) paste-ready text files from SSOT markdown."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONEPAGER = ROOT / "docs/final/artifacts/k_startup_majung_b2b_onepager_draft_v1.md"
OUT_DIR = ROOT / "reports/kstartup_majung_paste_ready"
META = ROOT / "reports/kstartup_majung_paste_ready_latest.json"

FILES = [
    ("bmo0902_step1_gwaje_nae_yong_paste.txt", "1. 아이템 개요"),
    ("bmo0902_need_problem_paste.txt", "2. 필요성 및 차별성"),
    ("bmo0902_solution_diff_paste.txt", "2. 필요성 및 차별성"),
    ("bmo0902_microsoft_synergy_paste.txt", "3. Microsoft 협업 시너지"),
    ("bmo0902_kpi_demo_paste.txt", "4. 과제 기간 내 KPI"),
    ("bmo0902_business_market_paste.txt", "5. 정확한 전략"),
    ("bmo0902_disclaimer_paste.txt", None),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_onepager() -> str:
    if not ONEPAGER.is_file():
        raise SystemExit(f"missing SSOT: {ONEPAGER}")
    return ONEPAGER.read_text(encoding="utf-8")


def _section(md: str, title: str) -> str:
    pattern = rf"^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, md, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _plain(md_chunk: str) -> str:
    text = md_chunk
    text = re.sub(r"^> .*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _disclaimer() -> str:
    base = ROOT / "reports/ms_rq019_paste_ready/disclaimer_footer_paste.txt"
    ms = base.read_text(encoding="utf-8").strip() if base.is_file() else ""
    return (
        "[K-Startup 마중 · 면책 · 붙여넣기용]\n\n"
        "본 제출 초안은 PoC·Azure 검증·내부 벤치 근거형 서술입니다. "
        "투자·매매·수익·적중률·무손실·100%·프로덕션 SLA·Track A 자동 승격·당선 단정을 하지 않습니다. "
        "47%·Jaccard 등 수치는 frozen bench·정책 하한 조건이며 RQ-017 ms 인과 연결은 주장하지 않습니다. "
        "ready_for_external_send=false — 법무 검토 전 대외 send 금지.\n\n"
        + ms
    )


def _step1(body: str) -> str:
    chunk = _section(body, "1. 아이템 개요 (Item Overview)")
    return (
        "[K-Startup Step1 · 과제내용 · SSOT onepager §1]\n\n"
        + _plain(chunk)
        + "\n\n(제외) 투자 자문·매매 지시·자동 매매·수익·적중률 보장."
    )


def _need_problem(body: str) -> str:
    chunk = _section(body, "2. 필요성 및 차별성 (Need & Differentiation)")
    problem = re.search(r"### 문제\s*\n(.*?)(?=###|\Z)", chunk, re.DOTALL)
    finops = re.search(r"### 2\.0 .*?\n(.*?)(?=### 문제|\Z)", chunk, re.DOTALL)
    parts = ["[K-Startup · 문제·필요성 · SSOT onepager §2]\n"]
    if finops:
        parts.append(_plain(finops.group(1)))
    if problem:
        parts.append(_plain(problem.group(1)))
    return "\n\n".join(parts)


def _solution_diff(body: str) -> str:
    chunk = _section(body, "2. 필요성 및 차별성 (Need & Differentiation)")
    solve = re.search(
        r"### 해결 및 차별성.*?\n(.*?)(?=### 2\.4|\Z)", chunk, re.DOTALL
    )
    text = _plain(solve.group(1)) if solve else _plain(chunk)
    return "[K-Startup · 해결·차별 · SSOT onepager §2]\n\n" + text


def _microsoft(body: str) -> str:
    chunk = _section(body, "3. Microsoft 협업 시너지 (Synergy)")
    return "[K-Startup · Microsoft/Azure · SSOT onepager §3]\n\n" + _plain(chunk)


def _kpi_demo(body: str) -> str:
    chunk = _section(body, "4. 과제 기간 내 KPI (수익·투기 지표 배제)")
    demo = (
        "\n\n[데모·검증 URL — PoC 시연용, 상용 SLA 아님]\n"
        "- Wire: https://jemaai.cloud/public_showroom_mkm_inter_agent_wire_v3.html\n"
        "- Oracle v6: https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1\n"
        "- Studio 진입: https://jema12.com/studio (→ v6 redirect, Cloudflare 규칙)\n"
        "- GIF(선택): reports/ms_rq019_paste_ready/ms_rq019_oracle_v6_visual_path_10s.gif"
    )
    return "[K-Startup · KPI·데모 · SSOT onepager §4]\n\n" + _plain(chunk) + demo


def _business_market(body: str) -> str:
    chunk = _section(body, "5. 정확한 전략 (SSOT — 2026-05-19)")
    one = re.search(r"### 5\.1 한 줄 정의\s*\n(.*?)(?=###|\Z)", chunk, re.DOTALL)
    parts = ["[K-Startup · 사업화·시장 · SSOT onepager §5]\n"]
    if one:
        parts.append(_plain(one.group(1)))
    portfolio = re.search(r"### 5\.3 포트폴리오.*?\n(.*?)(?=###|\Z)", chunk, re.DOTALL)
    if portfolio:
        parts.append(_plain(portfolio.group(1)))
    return "\n\n".join(parts)


def build() -> dict:
    body = _read_onepager()
    builders = {
        "bmo0902_step1_gwaje_nae_yong_paste.txt": lambda: _step1(body),
        "bmo0902_need_problem_paste.txt": lambda: _need_problem(body),
        "bmo0902_solution_diff_paste.txt": lambda: _solution_diff(body),
        "bmo0902_microsoft_synergy_paste.txt": lambda: _microsoft(body),
        "bmo0902_kpi_demo_paste.txt": lambda: _kpi_demo(body),
        "bmo0902_business_market_paste.txt": lambda: _business_market(body),
        "bmo0902_disclaimer_paste.txt": _disclaimer,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[dict] = []
    for name, fn in builders.items():
        text = fn() if callable(fn) else fn()
        path = OUT_DIR / name
        path.write_text(text.rstrip() + "\n", encoding="utf-8")
        written.append({"file": name, "chars": len(text), "path": path.as_posix()})

    order = OUT_DIR / "00_paste_order.txt"
    order.write_text(
        "\n".join(
            [
                "K-Startup 마중 BMO0902 붙여넣기 순서 (자동 생성)",
                "1) Step1 과제내용 → bmo0902_step1_gwaje_nae_yong_paste.txt",
                "2) 문제·필요성 → bmo0902_need_problem_paste.txt",
                "3) 해결·차별 → bmo0902_solution_diff_paste.txt",
                "4) Microsoft/Azure → bmo0902_microsoft_synergy_paste.txt",
                "5) KPI·데모 → bmo0902_kpi_demo_paste.txt",
                "6) 사업화·시장 → bmo0902_business_market_paste.txt",
                "7) 면책 하단 → bmo0902_disclaimer_paste.txt",
                "",
                "금지: 100%, lossless, Track A 승격, 당선 단정, 실매매·수익 보장",
                "매 화면 임시저장 · 최종 제출 human · passni SSO는 외부 Chrome/Edge",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    meta = {
        "schema": "kstartup_majung_paste_ready_v1",
        "generated_at_utc": _utc(),
        "ssot": ONEPAGER.relative_to(ROOT).as_posix(),
        "out_dir": OUT_DIR.relative_to(ROOT).as_posix(),
        "files": written,
        "paste_order": order.relative_to(ROOT).as_posix(),
        "ok": True,
    }
    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def main() -> int:
    meta = build()
    print(json.dumps({"ok": meta["ok"], "files": len(meta["files"]), "out_dir": meta["out_dir"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
