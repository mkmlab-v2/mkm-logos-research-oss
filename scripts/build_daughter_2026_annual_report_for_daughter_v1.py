#!/usr/bin/env python3
"""Print-friendly annual daughter-facing report from fact-check + monthly sequential SSOT."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/final/artifacts/daughter_2026_monthly_sequential_v1_latest.json"
DEFAULT_FC = ROOT / "docs/final/artifacts/family_anchor_fact_check_session_daughter_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/daughter_2026_annual_report_for_daughter_ko_v1_latest.md"

RESPONSE_KO = {
    "neutral": "보통",
    "sometimes": "가끔",
    "rarely": "거의 없음",
    "no": "아님",
    "yes": "예",
    "often": "자주",
    "none": "없음",
}

FACT_ROWS = [
    (
        "용돈·친구 비교가 스트레스?",
        ("wealth_pocket_money", "pocket_money_comparison_stress"),
    ),
    (
        "충동·단톡·간식에 돈 쓰는 편?",
        ("wealth_pocket_money", "impulse_or_group_chat_spending"),
    ),
    (
        "또래 중 특별히 좋아하는 사람? (연인 말고)",
        ("romance_peer", "peer_crush_or_affinity"),
    ),
    (
        "단톡·시선·역할(반장 등) 부담?",
        ("romance_peer", "group_chat_gaze_role_burden"),
    ),
    (
        "댄스·동아리 다음 날 학교 더 피곤?",
        ("sasang_lifestyle", "dance_next_day_fatigue"),
    ),
    (
        "늦잠·화장·세안 때문에 피부·컨디션 달라짐?",
        ("sasang_lifestyle", "late_sleep_makeup_skin_impact"),
    ),
]

# Canonical daughter-facing monthly copy (B-track reference; not prophecy).
ANNUAL_MONTH: dict[int, dict[str, str]] = {
    1: {
        "title": "친구·용돈·비교",
        "keyword": "친구, 나눔, 용돈",
        "feel": "비교 마음이 들 수 있는 시기",
        "help": "“필요 vs 충동” 가볍게 이야기 · **11:30 취침**",
        "daughter": "부담되면 **말하기**",
    },
    2: {
        "title": "새 학기·친구",
        "keyword": "친해지기, 단톡",
        "feel": "새 학기·교류가 늘 수 있는 시기",
        "help": "단톡 부담 **들어주기** · 가족·학원 **칭찬**",
        "daughter": "**인기**보다 **편한 친구**",
    },
    3: {
        "title": "솔직한 표현",
        "keyword": "말, 표현",
        "feel": "하고 싶은 말이 많아질 수 있음",
        "help": "솔직함 **칭찬** · 농담이 상처 될 수 있으면 **조절**",
        "daughter": "**반항**이 아니라 **의견**이라고 생각하기",
    },
    4: {
        "title": "모임·지출",
        "keyword": "활동, 지출",
        "feel": "모임·간식·지출 **가끔** (네 답과 같음)",
        "help": "활동비 **미리 합의**",
        "daughter": "늦잠·바쁨 겹치면 **수면** 먼저",
    },
    5: {
        "title": "바쁜 달",
        "keyword": "학교 피곤·바쁨 (**네가 말해 준 것과 맞음**)",
        "feel": "과제·일정이 몰릴 수 있음",
        "help": "성적 **숫자**보다 **잠·쉬는 시간**",
        "daughter": "버거우면 **“오늘 힘들어”** 한마디",
        "lived_star": True,
    },
    6: {
        "title": "역할·시선",
        "keyword": "발표, 반장, 시선",
        "feel": "역할·눈치 부담 **있을 수 있음** (확정 아님)",
        "help": "**짐 나눠 주기** · **쉬어도 된다**고 말하기",
        "daughter": "**연애·설렘** 프레임 말고 **부담**만 얘기해도 OK",
    },
    7: {
        "title": "인기·칭찬",
        "keyword": "칭찬, 역할",
        "feel": "칭찬·인기 **느낌**이 있을 수 있음",
        "help": "가족·학원 **격려**",
        "daughter": "부담되면 **집에** 말하기",
    },
    8: {
        "title": "학원·공부",
        "keyword": "학원, 멘토, 방학 루틴",
        "feel": "돈·연애 이슈보다 **공부·루틴**",
        "help": "방학 **늦잠**만 조금 관리",
        "daughter": "**댄스·취미** 유지",
    },
    9: {
        "title": "멘토·학습",
        "keyword": "2학기, 학원",
        "feel": "학원·멘토 쪽 **편한 달**",
        "help": "담임 **드라마** 기대 안 함",
        "daughter": "**공부 페이스** 네 속도로",
    },
    10: {
        "title": "일상 유지",
        "keyword": "루틴",
        "feel": "특별한 이슈 **없으면** 평온",
        "help": "**개입 최소**",
        "daughter": "수면·댄스·세안 **그대로**",
    },
    11: {
        "title": "연말·선물",
        "keyword": "선물, 모임, 비교",
        "feel": "지출·비교 **조금** 신경 쓸 수 있음",
        "help": "선물·용돈 **미리 합의**",
        "daughter": "비교 **스트레스** 있으면 말하기",
    },
    12: {
        "title": "연말",
        "keyword": "마무리, 따뜻함",
        "feel": "친구·가족 **교류** 좋은 시기",
        "help": "**한 해 수고** 인정",
        "daughter": "내년 **학원·일정** 가볍게만",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _axis_map(fc: dict) -> dict[str, dict]:
    return {a["axis"]: a for a in (fc.get("axes") or [])}


def _resp_ko(axis: dict, key: str, *, extra_qualifier: bool = False) -> str:
    val = (axis.get("responses") or {}).get(key, "")
    base = RESPONSE_KO.get(str(val), str(val))
    if extra_qualifier and key == "dance_next_day_fatigue":
        q = (axis.get("responses") or {}).get("dance_next_day_qualifier_ko")
        if q:
            return f"{base} ({q})"
    if key == "peer_crush_or_affinity" and val == "neutral":
        return "특별히 없음 (보통)"
    return base


def _month_symbols(month: dict, meta: dict) -> str:
    flags = month.get("peak_flags") or {}
    parts: list[str] = []
    if meta.get("lived_star"):
        parts.append("★")
    if flags.get("wealth_peak"):
        parts.append("🔸")
    if flags.get("romance_peer_peak"):
        parts.append("🔹")
    if flags.get("quiet_mentor_study"):
        parts.append("🟢")
    return " ".join(parts)


def _fact_summary(fc: dict) -> str:
    axes = _axis_map(fc)
    w = axes.get("wealth_pocket_money", {})
    r = axes.get("romance_peer", {})
    s = axes.get("sasang_lifestyle", {})
    cmp_stress = _resp_ko(w, "pocket_money_comparison_stress")
    impulse = _resp_ko(w, "impulse_or_group_chat_spending")
    return (
        f"비교·지출·또래는 **{cmp_stress}~{impulse}** 수준이고, "
        "**댄스 때문에 학교가 망가지진 않는다**고 했어. "
        "그래서 올해는 **수면·바쁜 학교 일정** 쪽을 더 챙기자."
    )


def build_report(doc: dict, fc: dict) -> str:
    axes = _axis_map(fc)
    ver = doc.get("version", "1.1.0")
    gen = doc.get("generated_at_utc") or _utc_now()
    month_by_n = {m["month"]: m for m in (doc.get("months") or [])}

    lines = [
        "# 2026학년도 가족 루틴·한 달 한 달 참고 보고서",
        "",
        "**대상:** 우리 딸  ",
        "**작성:** 가족 (MKM Life-Anchor · 참고용)  ",
        f"**작성일:** {gen[:10]}  ",
        f"**버전:** v{ver} (B-track 참고 · `research_only`)",
        "",
        "---",
        "",
        "## 1. 이 보고서를 읽기 전에",
        "",
        "이 문서는 **“올해 꼭 이렇게 된다”**는 예언이 **아닙니다.**  ",
        "엄마·아빠가 **네가 말해 준 체감**(5월 fact-check)과 **일상 루틴**을 바탕으로, "
        "바쁜 달에 **미리 짚어 두고 싶은 것**만 정리한 **가족 참고 보고서**입니다.",
        "",
        "- 성적·연애·용돈을 **숫자나 날짜로 단정하지 않습니다.**",
        "- **11시 30분쯤 자기**, **솔직하게 말하기**, **댄스·학교·친구** 같은 "
        "**네가 이미 알려준 것**을 우선합니다.",
        "- 이상하면 **언제든 말해 줘.** 보고서보다 **네 말**이 더 정확합니다.",
        "",
        "---",
        "",
        "## 2. 네가 알려 준 것 (2026년 5월, FACT)",
        "",
        "| 번호 | 내용 | 네 답 |",
        "|:---:|------|------|",
    ]
    for i, (q, (axis_name, key)) in enumerate(FACT_ROWS, 1):
        axis = axes.get(axis_name, {})
        extra = key == "dance_next_day_fatigue"
        ans = _resp_ko(axis, key, extra_qualifier=extra)
        lines.append(f"| {i} | {q} | **{ans}** |")

    lines += [
        "",
        f"**한 줄 요약:** {_fact_summary(fc)}",
        "",
        "---",
        "",
        "## 3. 2026년, 우리가 함께 지키면 좋은 것 (공통)",
        "",
        "| 구분 | 내용 |",
        "|------|------|",
        "| **학교·담임** | 담임선생님과 **적당한 거리**면 OK. 칭찬·응원은 **학원 선생님·가족**에서 많이 받자. |",
        "| **말하기** | **솔직하게 말하는 건 좋아.** 다만 말투만 부드럽게 하면 더 잘 통해. |",
        "| **수면** | **11시 30분쯤 자기** — 다음 날 학교가 덜 피곤해. |",
        "| **댄스** | **계속 해도 OK.** 다음 날 학교가 특별히 더 피곤하진 않다고 했지? **근육이 아프면 쉬어.** |",
        "| **용돈** | **필요한 것** vs **그냥 사고 싶은 것** — 가끔 같이 보면 돼. |",
        "| **친구·또래** | 호감·인기 이야기는 **자연스럽게.** **○월에 남친** 같은 말은 **우리 집 기준으로 안 해.** |",
        "",
        "---",
        "",
        "## 4. 2026년 월별 참고 (보고서 본문)",
        "",
        "> 아래는 **참고용 시나리오**입니다. **피크** 표시는 그달에 **비교·또래·학원** 중 "
        "**조금 더 신경 쓰면 좋은 달**이라는 뜻이지, **나쁜 달**이 아닙니다.",
        "",
    ]

    for mo in range(1, 13):
        meta = ANNUAL_MONTH[mo]
        seq = month_by_n.get(mo, {})
        sym = _month_symbols(seq, meta)
        sym_suffix = f" {sym}" if sym else ""
        lines += [
            f"### {mo}월 · {meta['title']}{sym_suffix}",
            "",
            "| 항목 | 참고 내용 |",
            "|------|-----------|",
            f"| **이달 키워드** | {meta['keyword']} |",
            f"| **체감** | {meta['feel']} |",
            f"| **우리가 도와줄 것** | {meta['help']} |",
            f"| **네가 하면 좋은 것** | {meta['daughter']} |",
            "",
        ]

    lines += [
        "---",
        "",
        "## 5. 기호 안내",
        "",
        "| 기호 | 의미 |",
        "|:---:|------|",
        "| 🔸 | 용돈·비교·지출 — **조금 더 이야기하면 좋은 달** |",
        "| 🔹 | 친구·또래·시선 — **부담 있으면 말해 주면 좋은 달** |",
        "| 🟢 | 학원·공부·멘토 — **루틴 유지가 잘 맞는 달** |",
        "| ★ | **네가 직접 말해 준 체감**과 맞는 달 (5월) |",
        "",
        "---",
        "",
        "## 6. 우리 집에서 하지 않기로 한 것",
        "",
        "1. **담임선생님**에게 과한 기대 · “9월 황금월” 같은 말  ",
        "2. **○월에 남친·연인** 같은 **단정**  ",
        "3. 성적·용돈을 **투자·재산**처럼 말하기  ",
        "4. **한약·병명**을 월마다 **억지로** 붙이기  ",
        "",
        "---",
        "",
        "## 7. 마무리",
        "",
        "올해도 **솔직하게**, **댄스도**, **친구도**, **공부도** — **네 페이스**가 제장 중요해.  ",
        "이 보고서는 **길잡이**일 뿐이고, **바뀌는 네 하루**가 항상 맞아.",
        "",
        "궁금하거나 “이건 아닌데?” 싶으면 **언제든** 엄마·아빠한테 말해 줘.",
        "",
        "---",
        "",
        f"*참고: 엄마·아빠용 상세 · mkmlife.com/oracle-sphere?profile=family · "
        f"SSOT v{ver} · B-track [HYPO] · Track A·임상·실매매와 무관*",
        "",
        f"*생성: `scripts/build_daughter_2026_annual_report_for_daughter_v1.py` · "
        f"`{_utc_now()}`*",
        "",
    ]
    # typo fix: 제장 -> 제일
    text = "\n".join(lines)
    return text.replace("제장 중요", "제일 중요")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--fact-check", type=Path, default=DEFAULT_FC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.json.is_file():
        raise SystemExit(f"missing sequential SSOT: {args.json}")
    if not args.fact_check.is_file():
        raise SystemExit(f"missing fact-check: {args.fact_check}")

    doc = json.loads(args.json.read_text(encoding="utf-8"))
    fc = json.loads(args.fact_check.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_report(doc, fc), encoding="utf-8")
    try:
        shown = args.out.relative_to(ROOT)
    except ValueError:
        shown = args.out
    print(f"Wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
