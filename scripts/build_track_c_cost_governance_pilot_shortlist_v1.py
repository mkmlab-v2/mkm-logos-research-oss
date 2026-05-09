#!/usr/bin/env python3
"""Build Track C Cost Governance pilot shortlist artifacts (json + markdown)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Candidate:
    name: str
    segment: str
    token_burden: int
    governance_need: int
    decision_velocity_need: int
    compliance_pressure: int
    integration_readiness: int
    why_now: str


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _score(c: Candidate) -> float:
    # Weighted toward immediate paid pilot conversion.
    return round(
        c.token_burden * 0.30
        + c.governance_need * 0.25
        + c.decision_velocity_need * 0.20
        + c.compliance_pressure * 0.10
        + c.integration_readiness * 0.15,
        3,
    )


def _candidates() -> list[Candidate]:
    return [
        Candidate("알파증권 리서치랩", "금융 리서치", 5, 5, 4, 5, 4, "월말 리포트 비용 급등 + 감사 추적 요구"),
        Candidate("브라보 손해보험 AI혁신팀", "보험/리스크", 4, 5, 4, 5, 4, "규제 대응형 로그·설명 책임이 강함"),
        Candidate("찰리 제조그룹 전략기획", "대기업 제조", 4, 4, 5, 4, 4, "분기 의사결정 속도 개선 니즈"),
        Candidate("델타 SaaS 고객지원본부", "SaaS CS", 5, 4, 5, 3, 5, "LLM 티켓 자동화로 토큰 사용량 폭증"),
        Candidate("에코 커머스 운영AI팀", "이커머스", 5, 4, 5, 3, 4, "프로모션 시즌 비용 스파이크 반복"),
        Candidate("폭스트롯 공공기관 디지털전환단", "공공/정책", 3, 5, 3, 5, 3, "정책 근거·기록 보존 필수"),
        Candidate("골프 헬스케어 플랫폼", "헬스케어 IT", 4, 4, 4, 5, 3, "민감도 높은 문구·기록 통제 필요"),
        Candidate("호텔 물류 최적화센터", "물류", 4, 4, 5, 3, 4, "실시간 운영판단 + 비용 예측 필요"),
        Candidate("인디 게임 퍼블리셔 AI툴팀", "게임", 5, 3, 4, 2, 5, "콘텐츠 생성 파이프라인 비용 통제 필요"),
        Candidate("줄리엣 컨설팅 인텔리전스팀", "컨설팅", 4, 4, 4, 4, 4, "고객사별 사용량/성과 리포트 필요"),
        Candidate("킬로 교육콘텐츠 플랫폼", "에듀테크", 4, 3, 4, 3, 4, "질의응답 트래픽 증가로 예산 압박"),
        Candidate("리마 핀테크 위험관리실", "핀테크", 5, 5, 4, 5, 3, "금융감독 대응 + 사용비 통제 동시 요구"),
    ]


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ranked = sorted(
        [
            {
                "name": c.name,
                "segment": c.segment,
                "score": _score(c),
                "why_now": c.why_now,
                "profile": {
                    "token_burden": c.token_burden,
                    "governance_need": c.governance_need,
                    "decision_velocity_need": c.decision_velocity_need,
                    "compliance_pressure": c.compliance_pressure,
                    "integration_readiness": c.integration_readiness,
                },
            }
            for c in _candidates()
        ],
        key=lambda x: x["score"],
        reverse=True,
    )

    top10 = ranked[:10]
    payload = {
        "schema": "track_c_cost_governance_pilot_shortlist_v1",
        "generated_at_utc": now,
        "selection_policy": {
            "target_count": 10,
            "scoring_formula": "0.30*token + 0.25*governance + 0.20*decision_velocity + 0.10*compliance + 0.15*integration",
            "note": "Track C Cost Governance Copilot pilot prioritization; business-facing shortlist only.",
        },
        "shortlist": top10,
    }

    root = _root()
    out_json = root / "docs/final/artifacts/track_c_cost_governance_pilot_shortlist_latest.json"
    out_md = root / "docs/final/artifacts/track_c_cost_governance_pilot_shortlist_latest.md"

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Track C Cost Governance Pilot Shortlist (Latest)",
        "",
        f"- generated_at_utc: `{now}`",
        "- schema: `track_c_cost_governance_pilot_shortlist_v1`",
        "- source: `scripts/build_track_c_cost_governance_pilot_shortlist_v1.py`",
        "",
        "| Rank | Candidate | Segment | Score | Why Now |",
        "|---|---|---|---:|---|",
    ]
    for i, item in enumerate(top10, start=1):
        lines.append(
            f"| {i} | {item['name']} | {item['segment']} | {item['score']:.3f} | {item['why_now']} |"
        )
    lines.append("")
    lines.append(
        "본 리스트는 파일럿 영업 우선순위 제안이며, 대외 약속·성과보장은 포함하지 않는다(Track C guardrails 준수)."
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

