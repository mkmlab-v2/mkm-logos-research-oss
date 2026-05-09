#!/usr/bin/env python3
"""Build personalized outreach pack for Track C Top 3 shortlist."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _segment_template(segment: str) -> str:
    s = segment.lower()
    if "금융" in segment or "핀테크" in segment or "보험" in segment:
        return (
            "안녕하세요, [담당자명]님.\n\n"
            "[회사명]의 AI 사용비 통제와 감사 대응을 동시에 강화하기 위한 "
            "Track C Cost Governance Copilot 파일럿을 제안드립니다.\n\n"
            "핵심 범위는 3가지입니다.\n"
            "- 예산캡/사용량 경보\n"
            "- 모델 라우팅 정책(비용-신뢰 균형)\n"
            "- 감사 로그 재구성 가능한 증적 패키지\n\n"
            "매수/매도 지시나 수익보장은 제공하지 않으며, "
            "운영 의사결정 보조만 제공합니다.\n\n"
            "20분 discovery call 가능하실까요? [옵션1], [옵션2] 중 편한 시간을 부탁드립니다.\n\n"
            "감사합니다.\n[보내는이]"
        )
    if "saas" in s or "cs" in s:
        return (
            "안녕하세요, [담당자명]님.\n\n"
            "[회사명]의 고객지원/운영 LLM 비용 급등 문제를 줄이기 위해 "
            "Track C Cost Governance Copilot 파일럿을 제안드립니다.\n\n"
            "핵심 범위는 3가지입니다.\n"
            "- 팀별/업무별 예산캡\n"
            "- 트래픽 구간별 모델 라우팅\n"
            "- 월간 비용-품질 감사 리포트\n\n"
            "성과 보장/자동 의사결정이 아닌, 운영팀의 통제력을 높이는 도구입니다.\n\n"
            "20분 discovery call 가능하실까요? [옵션1], [옵션2] 중 편한 시간을 부탁드립니다.\n\n"
            "감사합니다.\n[보내는이]"
        )
    return (
        "안녕하세요, [담당자명]님.\n\n"
        "[회사명] 대상 Track C Cost Governance Copilot 파일럿을 제안드립니다.\n"
        "비용 예측 가능성 + 감사 추적성을 동시에 강화하는 운영형 패키지입니다.\n\n"
        "20분 discovery call 가능하실까요? [옵션1], [옵션2] 중 편한 시간을 부탁드립니다.\n\n"
        "감사합니다.\n[보내는이]"
    )


def main() -> int:
    root = _root()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    shortlist_path = root / "docs/final/artifacts/track_c_cost_governance_pilot_shortlist_latest.json"
    shortlist = _load_json(shortlist_path)
    top3 = shortlist.get("shortlist", [])[:3]

    out_md = root / "docs/final/artifacts/track_c_b2b_outreach_top3_pack_latest.md"
    out_json = root / "docs/final/artifacts/track_c_b2b_outreach_top3_pack_latest.json"

    pack = {
        "schema": "track_c_b2b_outreach_top3_pack_v1",
        "generated_at_utc": now,
        "source_shortlist": str(shortlist_path.relative_to(root)).replace("\\", "/"),
        "targets": [],
    }

    lines = [
        "# Track C B2B Outreach Top3 Pack (Latest)",
        "",
        f"- generated_at_utc: `{now}`",
        "- schema: `track_c_b2b_outreach_top3_pack_v1`",
        "- source: `scripts/build_track_c_top3_outreach_pack_v1.py`",
        "",
        "아래 템플릿은 Top3 대상 맞춤형 초안이며, 발송 전 `[회사명]`, `[담당자명]`, `[옵션1/2]`를 교체합니다.",
        "",
    ]

    for idx, target in enumerate(top3, start=1):
        name = target["name"]
        segment = target["segment"]
        score = target["score"]
        why = target["why_now"]
        subject = f"[{name}] AI 사용비 통제 파일럿 제안 (Track C Cost Governance)"
        body = _segment_template(segment)

        pack["targets"].append(
            {
                "rank": idx,
                "name": name,
                "segment": segment,
                "score": score,
                "why_now": why,
                "subject": subject,
                "body": body,
            }
        )

        lines.extend(
            [
                f"## {idx}) {name} ({segment})",
                "",
                f"- score: `{score}`",
                f"- why_now: {why}",
                "",
                "### 제목",
                "",
                subject,
                "",
                "### 본문",
                "",
                body,
                "",
                "---",
                "",
            ]
        )

    out_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

