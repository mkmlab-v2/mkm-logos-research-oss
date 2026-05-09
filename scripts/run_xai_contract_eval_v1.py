#!/usr/bin/env python3
"""Evaluate XAI output-contract compliance over a question sample set.

Default flow:
1) Read template questions (`xai_sample_20_eval_template_v1.json`)
2) Read response rows (`xai_sample_20_eval_responses_latest.json`)
3) Score contract checks and write eval artifact (`xai_contract_eval_latest.json`)

Research / governance only. Not a trading trigger.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "docs" / "final" / "artifacts" / "xai_sample_20_eval_template_v1.json"
DEFAULT_RESPONSES = ROOT / "docs" / "final" / "artifacts" / "xai_sample_20_eval_responses_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "xai_contract_eval_latest.json"
DEFAULT_FAIL_OUT = ROOT / "docs" / "final" / "artifacts" / "xai_contract_failures_latest.json"
DEFAULT_BOOTSTRAP = ROOT / "docs" / "final" / "artifacts" / "xai_sample_20_eval_responses_latest.json"

SCHEMA = "xai_contract_eval_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _to_response_map(responses_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = responses_doc.get("responses")
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        q = row.get("question") if isinstance(row.get("question"), dict) else {}
        qid = q.get("question_id")
        if _is_nonempty_str(qid):
            out[str(qid)] = row
    return out


def _evaluate_row(question: dict[str, Any], response: dict[str, Any] | None) -> dict[str, Any]:
    qid = str(question.get("question_id") or "")
    result: dict[str, Any] = {
        "question_id": qid,
        "domain_tag": question.get("domain_tag"),
        "priority": question.get("priority"),
    }
    if not response:
        result["checks"] = {
            "has_conclusion_one_line": False,
            "has_evidence_3plus": False,
            "has_limitation_one": False,
            "has_action_guide_one": False,
            "has_claim_type_labels": False,
            "has_confidence_0_1": False,
            "has_contract_pass_flag": False,
        }
        result["contract_pass"] = False
        result["note"] = "missing_response_for_question"
        return result

    final_output = response.get("final_output") if isinstance(response.get("final_output"), dict) else {}
    evidence = response.get("evidence") if isinstance(response.get("evidence"), list) else []
    limitation = response.get("limitation") if isinstance(response.get("limitation"), dict) else {}
    action_guide = response.get("action_guide") if isinstance(response.get("action_guide"), dict) else {}
    evaluation = response.get("evaluation") if isinstance(response.get("evaluation"), dict) else {}

    has_conclusion = _is_nonempty_str(final_output.get("conclusion_one_line"))
    has_evidence_3plus = len(evidence) >= 3
    has_limitation = _is_nonempty_str(limitation.get("limitation_one"))
    has_action = _is_nonempty_str(action_guide.get("action_guide_one"))

    has_claim_labels = True
    has_confidence = True
    for ev in evidence:
        if not isinstance(ev, dict):
            has_claim_labels = False
            has_confidence = False
            continue
        claim_type = ev.get("claim_type")
        if claim_type not in ("FACT", "HYPO"):
            has_claim_labels = False
        conf = ev.get("confidence_0_1")
        if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
            has_confidence = False

    has_contract_pass_flag = isinstance(evaluation.get("contract_pass"), bool)
    strict_pass = (
        has_conclusion
        and has_evidence_3plus
        and has_limitation
        and has_action
        and has_claim_labels
        and has_confidence
    )

    result["checks"] = {
        "has_conclusion_one_line": has_conclusion,
        "has_evidence_3plus": has_evidence_3plus,
        "has_limitation_one": has_limitation,
        "has_action_guide_one": has_action,
        "has_claim_type_labels": has_claim_labels,
        "has_confidence_0_1": has_confidence,
        "has_contract_pass_flag": has_contract_pass_flag,
    }
    result["contract_pass"] = strict_pass
    result["response_contract_pass_field"] = evaluation.get("contract_pass") if has_contract_pass_flag else None
    if has_contract_pass_flag and bool(evaluation.get("contract_pass")) != strict_pass:
        result["note"] = "contract_pass_mismatch_between_field_and_recomputed"
    return result


def _bootstrap_from_template(template_doc: dict[str, Any], out_path: Path) -> None:
    questions = template_doc.get("questions") if isinstance(template_doc.get("questions"), list) else []
    responses: list[dict[str, Any]] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        responses.append(
            {
                "schema": "xai_decision_trace_contract_v1",
                "version": "v1",
                "decision_trace_id": f"trace_{q.get('question_id', 'unknown')}",
                "question": {
                    "question_id": q.get("question_id"),
                    "text": q.get("text"),
                    "domain_tag": q.get("domain_tag"),
                },
                "final_output": {"conclusion_one_line": ""},
                "evidence": [],
                "limitation": {"limitation_one": ""},
                "action_guide": {"action_guide_one": ""},
                "evaluation": {
                    "evidence_count_ok": False,
                    "has_limitation": False,
                    "has_action_guide": False,
                    "contract_pass": False,
                    "review_note": "bootstrap_empty_template_fill_required",
                },
            }
        )
    payload = {
        "schema": "xai_sample_20_eval_responses_v1",
        "version": "v1",
        "generated_at_utc": _utc_now(),
        "source_template": _norm(DEFAULT_TEMPLATE),
        "responses": responses,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _autofill_demo_responses(template_doc: dict[str, Any], out_path: Path) -> None:
    questions = template_doc.get("questions") if isinstance(template_doc.get("questions"), list) else []
    responses: list[dict[str, Any]] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        qid = str(q.get("question_id") or "unknown")
        qtext = str(q.get("text") or "")
        dtag = str(q.get("domain_tag") or "general")
        conclusion = f"{dtag} 관점에서 현재 병목은 데이터 정합성과 출력 계약 미준수의 결합으로 보인다."
        responses.append(
            {
                "schema": "xai_decision_trace_contract_v1",
                "version": "v1",
                "decision_trace_id": f"trace_{qid}",
                "question": {
                    "question_id": qid,
                    "text": qtext,
                    "domain_tag": dtag,
                },
                "final_output": {"conclusion_one_line": conclusion},
                "evidence": [
                    {
                        "evidence_id": f"{qid}_ev1",
                        "source_type": "artifact",
                        "source_id": "docs/final/artifacts/xai_contract_eval_latest.json",
                        "claim_type": "FACT",
                        "evidence_text": "직전 평가에서 contract pass rate가 기준 미달로 확인되었다.",
                        "confidence_0_1": 0.9,
                        "relation_to_conclusion": "supports",
                    },
                    {
                        "evidence_id": f"{qid}_ev2",
                        "source_type": "internal_doc",
                        "source_id": "docs/final/artifacts/logos_symbolic_paid_user_brief_latest.md",
                        "claim_type": "FACT",
                        "evidence_text": "출력 계약은 결론/근거/한계/행동 가이드를 필수 구조로 요구한다.",
                        "confidence_0_1": 0.85,
                        "relation_to_conclusion": "supports",
                    },
                    {
                        "evidence_id": f"{qid}_ev3",
                        "source_type": "other",
                        "source_id": "ops_review_hypothesis_v1",
                        "claim_type": "HYPO",
                        "evidence_text": "도메인별 질문 분포 변화가 품질 저하를 가속했을 가능성이 있다.",
                        "confidence_0_1": 0.6,
                        "relation_to_conclusion": "context",
                    },
                ],
                "limitation": {
                    "limitation_one": "현재 결론은 샘플 기반 진단이며 전체 기간 회귀 검증은 추가로 필요하다."
                },
                "action_guide": {
                    "action_guide_one": "해당 도메인 상위 실패 5건을 우선 보강해 다음 평가 주기에 재측정한다."
                },
                "evaluation": {
                    "evidence_count_ok": True,
                    "has_limitation": True,
                    "has_action_guide": True,
                    "contract_pass": True,
                    "review_note": "demo_autofill_v1",
                },
            }
        )
    payload = {
        "schema": "xai_sample_20_eval_responses_v1",
        "version": "v1",
        "generated_at_utc": _utc_now(),
        "source_template": _norm(DEFAULT_TEMPLATE),
        "responses": responses,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template-json", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--responses-json", type=Path, default=DEFAULT_RESPONSES)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--failures-output", type=Path, default=DEFAULT_FAIL_OUT)
    ap.add_argument("--min-pass-rate", type=float, default=0.9, help="Go/hold threshold (default 0.9).")
    ap.add_argument("--bootstrap-empty-responses", action="store_true")
    ap.add_argument("--autofill-demo-responses", action="store_true")
    ap.add_argument("--bootstrap-output", type=Path, default=DEFAULT_BOOTSTRAP)
    args = ap.parse_args()

    if not args.template_json.is_file():
        print(f"missing_template: {args.template_json}", file=sys.stderr)
        return 2

    template_doc = _load_json(args.template_json)
    if args.bootstrap_empty_responses:
        _bootstrap_from_template(template_doc, args.bootstrap_output)
        print(str(args.bootstrap_output.resolve()))
        return 0
    if args.autofill_demo_responses:
        _autofill_demo_responses(template_doc, args.bootstrap_output)
        print(str(args.bootstrap_output.resolve()))
        return 0

    if not args.responses_json.is_file():
        print(
            f"missing_responses: {args.responses_json} (run with --bootstrap-empty-responses first)",
            file=sys.stderr,
        )
        return 2

    responses_doc = _load_json(args.responses_json)
    response_map = _to_response_map(responses_doc)
    questions = template_doc.get("questions") if isinstance(template_doc.get("questions"), list) else []

    row_results: list[dict[str, Any]] = []
    pass_count = 0
    for q in questions:
        if not isinstance(q, dict):
            continue
        qid = str(q.get("question_id") or "")
        rr = _evaluate_row(q, response_map.get(qid))
        row_results.append(rr)
        if rr.get("contract_pass") is True:
            pass_count += 1

    total = len(row_results)
    pass_rate = (pass_count / total) if total else 0.0
    decision = "GO_CONTRACT_READY" if pass_rate >= args.min_pass_rate else "HOLD_CONTRACT_GAP"
    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "inputs": {
            "template_json": _norm(args.template_json),
            "responses_json": _norm(args.responses_json),
            "min_pass_rate": args.min_pass_rate,
        },
        "metrics": {
            "total_questions": total,
            "pass_count": pass_count,
            "pass_rate": round(pass_rate, 6),
            "fail_count": max(0, total - pass_count),
        },
        "decision": decision,
        "rows": row_results,
        "note": "Contract requires conclusion one-line + >=3 evidence + one limitation + one action guide.",
    }
    failed_rows = [r for r in row_results if not bool(r.get("contract_pass"))]
    fail_out = {
        "schema": "xai_contract_failures_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "template_json": _norm(args.template_json),
            "responses_json": _norm(args.responses_json),
            "min_pass_rate": args.min_pass_rate,
        },
        "metrics": {
            "total_questions": total,
            "fail_count": len(failed_rows),
            "fail_rate": round((len(failed_rows) / total), 6) if total else 0.0,
        },
        "rows": failed_rows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.failures_output.parent.mkdir(parents=True, exist_ok=True)
    args.failures_output.write_text(json.dumps(fail_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
