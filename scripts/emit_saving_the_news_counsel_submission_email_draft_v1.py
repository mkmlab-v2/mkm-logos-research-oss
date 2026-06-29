#!/usr/bin/env python3
"""Emit counsel submission email draft (commander sends — agent does not mail)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
BENCH = ART / "saving_the_news_news_rt_bench_result_v1_latest.json"
DEFAULT_OUT = ART / "saving_the_news_counsel_submission_email_draft_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict[str, Any]:
    bench = _read(BENCH) or {}
    kpi = bench.get("kpi") or {}
    n_rows = bench.get("observation_row_count", "?")
    saving = kpi.get("token_saving_ratio", "?")
    jacc = kpi.get("jaccard_fidelity_proxy", "?")
    body = f"""안녕하세요, 법무팀님.

MKM Track C 「Saving the News」 B2B 관측·게이트 레이어 — 대외 카피·저작권 포지션 검토 요청드립니다.

첨부: saving_the_news_counsel_export_pack_v1.zip
포함: blueprint, Perplexity 근거, Track C 1p, Phase1 scope, 로드맵 클로저, PUBLIC_FACING v1.7,
      NEWS-RT 벤치(n={n_rows}, saving≈{saving}, J≈{jacc}), finance hypo 격리 JSON, B2B panel slice

운영 참고(검토용 URL · research_only):
- 소비자 관측 덱: https://mkmlife.com/news-deck (5-card · 세계/경제 RSS · 포털 아님)
- B2B 쇼룸: https://jemaai.cloud/legacy/public_showroom_saving_the_news_matrix_v1.html

확인 요청:
1. 「기사 전체 크롤링·자동 요약 대체」에 해당하지 않는지 (문체부·저작권위 2026-02-26 공정이용 안내서 사례)
2. State Card·Matrix·RSS ingest의 시장 대체·공정이용 리스크
3. onepager 면책·GTM 3문장 적합성
4. ready_for_external_send 승격 전 체크리스트

본 제품은 research_only·promote HOLD이며, zero hallucination·뉴스 포털·Track A 수치(47.5%) 주장을 하지 않습니다.
Finance hypo 축은 메인 덱·NEWS-RT 주장과 합선하지 않습니다.

회신 티켓/이메일 ID는 record_saving_the_news_legal_counsel_signoff_v1.py --counsel-reference 로 기록 예정입니다.

감사합니다.
MKM Ops (INTERNAL)"""
    return {
        "schema": "saving_the_news_counsel_submission_email_draft_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "lane": "research_only",
        "send_status": "DRAFT_ONLY_NOT_SENT",
        "ready_for_external_send": False,
        "suggested_subject": "[MKM][Track C] Saving the News — B2B copy & KR copyright posture review (W3 pack)",
        "attachment": "saving_the_news_counsel_export_pack_v1.zip",
        "body_ko": body,
        "boundary_ack": "Agent cannot send mail; commander sends from org mailbox.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
