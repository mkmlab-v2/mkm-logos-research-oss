#!/usr/bin/env python3
"""Build xai_runtime_answers_v1 from 20-question eval template.

Creates runtime input rows for each template question so the
runtime->contract mapping pipeline can run end-to-end.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "docs" / "final" / "artifacts" / "xai_sample_20_eval_template_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "xai_runtime_answers_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template-json", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()

    doc = _load(ns.template_json)
    questions = doc.get("questions") if isinstance(doc.get("questions"), list) else []

    answers: list[dict[str, Any]] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        qid = str(q.get("question_id") or "unknown")
        qtext = str(q.get("text") or "")
        dtag = str(q.get("domain_tag") or "general")
        answers.append(
            {
                "question_id": qid,
                "question_text": qtext,
                "domain_tag": dtag,
                "decision_trace_id": f"trace_{qid}_runtime",
                "conclusion_one_line": f"{dtag} 관점에서 현재 핵심 이슈는 계약 준수 품질 편차다.",
                "evidence": [
                    {
                        "evidence_id": f"{qid}_ev1",
                        "source_type": "artifact",
                        "source_id": "docs/final/artifacts/xai_contract_eval_latest.json",
                        "claim_type": "FACT",
                        "evidence_text": "직전 평가 산출물에서 계약 준수 여부를 확인할 수 있다.",
                        "confidence_0_1": 0.9,
                        "relation_to_conclusion": "supports",
                    },
                    {
                        "evidence_id": f"{qid}_ev2",
                        "source_type": "internal_doc",
                        "source_id": "docs/final/artifacts/logos_symbolic_paid_user_brief_latest.md",
                        "claim_type": "FACT",
                        "evidence_text": "출력 계약은 결론/근거/한계/행동 가이드 포함을 필수로 정의한다.",
                        "confidence_0_1": 0.85,
                        "relation_to_conclusion": "supports",
                    },
                    {
                        "evidence_id": f"{qid}_ev3",
                        "source_type": "log",
                        "source_id": "reports/xai_contract_daily_gate_log.jsonl",
                        "claim_type": "HYPO",
                        "evidence_text": "운영 로그 추세상 도메인별 편차가 성과에 영향을 줄 가능성이 있다.",
                        "confidence_0_1": 0.6,
                        "relation_to_conclusion": "context",
                    },
                ],
                "limitation_one": "현재 진단은 최근 샘플 기준이며 장기 검증 보강이 필요하다.",
                "action_guide_one": "상위 실패군 5건을 우선 교정하고 다음 주기에 재평가한다.",
                "review_note": "runtime_autofill_template_v1",
            }
        )

    out = {
        "schema": "xai_runtime_answers_v1",
        "generated_at_utc": _utc_now(),
        "source": "template_autofill_v1",
        "answers": answers,
    }
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(ns.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
