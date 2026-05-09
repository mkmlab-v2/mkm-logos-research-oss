#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot MKM myeongni autobot entrypoint.

Single command in, full structured report + bot answer out.
Designed to remove manual multi-command chaining at runtime.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_myeongni_full_report_v1 import _build_report, _from_run_cli


def _bot_answer(report: dict, user_prompt: str) -> str:
    p = report.get("pillars") or {}
    dm = report.get("day_master") or {}
    sa = report.get("structure_analysis") or {}
    ep = sa.get("element_profile") or {}
    sh = sa.get("day_master_strength_hint") or {}
    af = report.get("annual_fortune") or {}
    rows = af.get("rows") or []
    head = rows[:3]

    lines: list[str] = []
    lines.append("## 자동 고도화 명리 답변")
    lines.append(f"- 질의: {user_prompt or '일반 해석'}")
    lines.append(f"- 원국: {p.get('year')} / {p.get('month')} / {p.get('day')} / {p.get('hour')}")
    lines.append(f"- 일간: {dm.get('stem_hangul')} ({dm.get('stem_element_hint')})")
    ec = ep.get("element_counts_visible") or {}
    lines.append(
        f"- 오행 가시 분포: 목 {ec.get('목',0)} 화 {ec.get('화',0)} 토 {ec.get('토',0)} 금 {ec.get('금',0)} 수 {ec.get('수',0)}"
    )
    lines.append(
        f"- 강약 힌트: {sh.get('strength_label')} (계절={sh.get('season_element_hint')}, 월지={sh.get('month_branch')})"
    )
    if head:
        preview = ", ".join([f"{r.get('year')}:{r.get('sewoon_pillar')}/{r.get('sewoon_stem_ten_god')}" for r in head])
        lines.append(f"- 근년 세운 요약: {preview}")
    lines.append("- 해석 포인트: 실행/책임 축(목)과 관리/축적 축(토)이 동시에 강한 구조로 읽히며, 월별 변동은 월운 표에서 확인 가능.")
    lines.append(
        "- 주의: 이 출력은 상징 해석 자동화이며, 의료/법률/투자 의사결정의 단독 근거로 사용하지 마세요."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run one-shot MKM myeongni autobot.")
    ap.add_argument("--name", default="user")
    ap.add_argument("--local", nargs=6, type=int, metavar=("Y", "M", "D", "h", "m", "s"), required=True)
    ap.add_argument("--iana-tz", default="Asia/Seoul")
    ap.add_argument("--is-male", action="store_true")
    ap.add_argument("--user-prompt", default="")
    ap.add_argument("--annual-start-year", type=int, default=datetime.now().year)
    ap.add_argument("--annual-years", type=int, default=5)
    ap.add_argument("--monthly-months-per-year", type=int, default=3)
    ap.add_argument("--out-json", type=Path, default=ROOT / "reports" / "myeongni_autobot_latest.json")
    ap.add_argument("--out-md", type=Path, default=ROOT / "reports" / "myeongni_autobot_latest.md")
    args = ap.parse_args()

    birth = _from_run_cli(
        args.local[0],
        args.local[1],
        args.local[2],
        args.local[3],
        args.local[4],
        args.local[5],
        args.iana_tz,
        args.is_male,
    )
    report = _build_report(
        birth,
        args.annual_start_year,
        args.annual_years,
        max(0, min(12, args.monthly_months_per_year)),
    )
    answer = _bot_answer(report, args.user_prompt)
    payload = {
        "schema": "myeongni_autobot_response_v1",
        "name": args.name,
        "report": report,
        "answer_markdown": answer,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(answer, encoding="utf-8")

    print(f"WROTE: {args.out_json}")
    print(f"WROTE: {args.out_md}")
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

