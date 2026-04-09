#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _rows_medical(n: int) -> list[dict[str, str]]:
    dx = ["고혈압", "당뇨병", "고지혈증", "천식", "빈혈"]
    plan = ["생활습관 교정", "약물 복용 유지", "정기 추적검사", "식이 조절", "운동 처방"]
    out = []
    for i in range(n):
        d = dx[i % len(dx)]
        p = plan[(i * 2) % len(plan)]
        src = f"환자 {i+1}의 주진단은 {d}이며 2주 내 {p}이 필요하다."
        if i % 4 == 0:
            pred = src.replace("필요하다", "요구된다")
        elif i % 4 == 1:
            pred = src.replace("주진단은", "진단은")
        elif i % 4 == 2:
            pred = src.replace("2주 내", "단기적으로")
        else:
            pred = src
        out.append({"source_text": src, "predicted_text": pred})
    return out


def _rows_finance(n: int) -> list[dict[str, str]]:
    regime = ["변동성 확대", "위험자산 선호", "긴축 국면", "완화 기대", "중립 횡보"]
    act = ["현금 비중 상향", "헤지 비중 유지", "분할 매수", "익절 비율 확대", "리밸런싱 실행"]
    out = []
    for i in range(n):
        r = regime[i % len(regime)]
        a = act[(i * 3) % len(act)]
        src = f"포트폴리오 {i+1}은 {r} 신호로 판단되어 {a} 전략을 적용한다."
        if i % 4 == 0:
            pred = src.replace("적용한다", "수행한다")
        elif i % 4 == 1:
            pred = src.replace("신호로 판단되어", "신호를 근거로")
        elif i % 4 == 2:
            pred = src.replace("포트폴리오", "계정")
        else:
            pred = src
        out.append({"source_text": src, "predicted_text": pred})
    return out


def _rows_policy(n: int) -> list[dict[str, str]]:
    policy = ["PII 마스킹", "권한 최소화", "감사 로그 보존", "요청 속도 제한", "비밀키 순환"]
    scope = ["운영 API", "관리자 API", "내부 배치", "외부 웹훅", "모니터링 채널"]
    out = []
    for i in range(n):
        p = policy[i % len(policy)]
        s = scope[(i * 4) % len(scope)]
        src = f"정책 항목 {i+1}은 {s}에서 {p} 규칙을 강제한다."
        if i % 4 == 0:
            pred = src.replace("강제한다", "적용한다")
        elif i % 4 == 1:
            pred = src.replace("정책 항목", "정책 규칙")
        elif i % 4 == 2:
            pred = src.replace("에서", "구간에서")
        else:
            pred = src
        out.append({"source_text": src, "predicted_text": pred})
    return out


def _write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate Track B domain pair datasets.")
    ap.add_argument("--count-per-domain", type=int, default=100)
    args = ap.parse_args()

    n = args.count_per_domain
    out_med = ART / "trackb_semantic_eval_pairs_medical_v1.jsonl"
    out_fin = ART / "trackb_semantic_eval_pairs_finance_v1.jsonl"
    out_pol = ART / "trackb_semantic_eval_pairs_policy_v1.jsonl"

    _write_jsonl(out_med, _rows_medical(n))
    _write_jsonl(out_fin, _rows_finance(n))
    _write_jsonl(out_pol, _rows_policy(n))

    print(str(out_med))
    print(str(out_fin))
    print(str(out_pol))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
