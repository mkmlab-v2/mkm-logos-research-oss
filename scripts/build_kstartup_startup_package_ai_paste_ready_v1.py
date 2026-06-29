#!/usr/bin/env python3
"""Build K-Startup 창업패키지 AI 인재 실증형 paste-ready files from graft SSOT."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from kstartup_startup_package_ai_form_notice_compliance_v1 import (  # noqa: E402
    apply_form_notice_compliance,
)
GRAFT = ROOT / "docs/final/artifacts/startup_package_ai_2026_submission_graft_v1.md"
TECH_REUSE = ROOT / "reports/kstartup_startup_package_ai_honest_tech_reuse_one_page_v1.md"
OUT_DIR = ROOT / "reports/kstartup_startup_package_ai_paste_ready"
META = ROOT / "reports/kstartup_startup_package_ai_paste_ready_latest.json"

FILES = [
    ("plan_01_summary_paste.txt", "1. 사업개요 (Executive Summary)"),
    ("plan_02_market_problem_paste.txt", "2. 시장분석 및 문제인식"),
    ("plan_03_tech_roadmap_paste.txt", "3. 기술개발 및 사업화 추진계획"),
    ("plan_04_growth_funding_paste.txt", "4. 성장전략 및 자금 사용"),
    ("plan_05_team_paste.txt", "5. 팀 구성 및 역량"),
    ("plan_06_ai_talent_2p_paste.txt", "6. AI 인재 활용 계획 (별첨 2p 요약)"),
    ("plan_disclaimer_paste.txt", None),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_graft() -> str:
    if not GRAFT.is_file():
        raise SystemExit(f"missing SSOT: {GRAFT}")
    return GRAFT.read_text(encoding="utf-8")


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
    return (
        "[창업패키지 AI 인재 실증형 · 면책 · 붙여넣기용]\n\n"
        "본 초안은 PoC·내부 벤치·Fact-Lock 근거형 서술입니다. "
        "투자·매매·수익·적중률·무손실·100%·프로덕션 SLA·Track A 실매매·당선·협약 단정을 하지 않습니다. "
        "압축률·토큰 절감 수치는 본 과제 범위와 합선하지 않습니다. "
        "ready_for_external_send=false — 제출 전 대표자 육안·금지어 스캔 필수.\n"
    )


def _run_submission_gate(*, draft_ok: bool) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/check_kstartup_startup_package_ai_submission_gate_v1.py"),
    ]
    if draft_ok:
        cmd.append("--draft-ok")
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build 340 paste pack from graft SSOT.")
    ap.add_argument(
        "--strict-submission-gate",
        action="store_true",
        help="Exit 1 if human blocker gates incomplete (default: build allowed, gate reported).",
    )
    args = ap.parse_args()

    body = _read_graft()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for fname, heading in FILES:
        if heading is None:
            content = _disclaimer()
        else:
            chunk = _section(body, heading)
            content = f"[창업패키지 · {heading} · graft v1]\n\n" + _plain(chunk)
            if fname == "plan_03_tech_roadmap_paste.txt" and TECH_REUSE.is_file():
                tr = TECH_REUSE.read_text(encoding="utf-8")
                tr_body = _section(tr, "2. 기존 R&D를 “버리지 않고” 재배치 (정직)")
                tr_pipe = _section(tr, "3. 파이프라인 (5단 · 측정 가능)")
                tr_cost = _section(tr, "4. 비용·품질 (과장 없이)")
                extra = "\n\n---\n\n[기술 재사용 · Fact-Safe · tech_reuse_1p]\n\n"
                for part in (tr_body, tr_pipe, tr_cost):
                    if part:
                        extra += _plain(part) + "\n\n"
                content = content.rstrip() + extra.rstrip() + "\n"
            content = apply_form_notice_compliance(content, context=fname)
        path = OUT_DIR / fname
        path.write_text(content, encoding="utf-8")
        written.append(fname)

    order = (
        "붙여넣기 순서 (별첨1 양식 칸명에 맞게 매핑 — 양식 1:1 대조 필수)\n"
        "1. plan_01_summary_paste.txt → 사업개요/요약\n"
        "2. plan_02_market_problem_paste.txt → 시장·문제인식\n"
        "3. plan_03_tech_roadmap_paste.txt → 기술·추진계획\n"
        "4. plan_04_growth_funding_paste.txt → 성장·자금\n"
        "5. plan_05_team_paste.txt → 팀 역량\n"
        "6. plan_06_ai_talent_2p_paste.txt → AI 인재 활용 2p (별도 첨부)\n"
        "7. plan_disclaimer_paste.txt → 각 섹션 하단 또는 부록(선택)\n"
    )
    (OUT_DIR / "00_paste_order.txt").write_text(order, encoding="utf-8")
    written.append("00_paste_order.txt")

    META.write_text(
        json.dumps(
            {
                "schema": "kstartup_startup_package_ai_paste_ready_v1",
                "generated_at_utc": _utc(),
                "graft_ssot": str(GRAFT.relative_to(ROOT)).replace("\\", "/"),
                "out_dir": str(OUT_DIR.relative_to(ROOT)).replace("\\", "/"),
                "files": written,
                "deadline_kst": "2026-06-12T18:00:00+09:00",
                "recommend_apply_by_kst": "2026-06-10",
                "boundary_ack": "Paste pack does not imply eligibility pass or selection.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(str(META))
    gate_rc = _run_submission_gate(draft_ok=not args.strict_submission_gate)
    if args.strict_submission_gate and gate_rc != 0:
        return gate_rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
