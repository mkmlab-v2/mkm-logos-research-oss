#!/usr/bin/env python3
"""Build xai_runtime_answers_v1 from operational artifacts/logs.

This adapter creates q01~q20 runtime answers grounded on existing repo artifacts.
It is deterministic and file-based for daily unattended execution.
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
DEFAULT_GATE_LOG = ROOT / "reports" / "xai_contract_daily_gate_log.jsonl"
DEFAULT_FAILURES = ROOT / "docs" / "final" / "artifacts" / "xai_contract_failures_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _exists(path: Path) -> bool:
    return path.is_file()


def _artifact_evidence() -> list[dict[str, str]]:
    return [
        {"id": "artifact_eval", "path": "docs/final/artifacts/xai_contract_eval_latest.json"},
        {"id": "artifact_failures", "path": "docs/final/artifacts/xai_contract_failures_latest.json"},
        {"id": "artifact_gate", "path": "docs/final/artifacts/xai_contract_daily_gate_summary_latest.json"},
        {"id": "ops_log", "path": "reports/xai_contract_daily_gate_log.jsonl"},
    ]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _metrics_snapshot() -> dict[str, Any]:
    logs = _load_jsonl(DEFAULT_GATE_LOG)
    total = len(logs)
    hold = len([r for r in logs if str(r.get("status") or "") == "HOLD"])
    warning = len([r for r in logs if str(r.get("severity") or "") == "warning"])
    critical = len([r for r in logs if str(r.get("severity") or "") == "critical"])
    pass_rate_mean = 0.0
    if total > 0:
        vals = [float(r.get("pass_rate") or 0.0) for r in logs]
        pass_rate_mean = round(sum(vals) / len(vals), 6)
    fail_doc = _load_json(DEFAULT_FAILURES)
    fail_rows = fail_doc.get("rows") if isinstance(fail_doc.get("rows"), list) else []
    fail_count = len([r for r in fail_rows if isinstance(r, dict)])
    return {
        "total_runs": total,
        "hold_runs": hold,
        "warning_runs": warning,
        "critical_runs": critical,
        "pass_rate_mean": pass_rate_mean,
        "fail_count": fail_count,
    }


def _build_evidence_triplet(qid: str, metrics: dict[str, Any]) -> list[dict[str, Any]]:
    refs = _artifact_evidence()
    out: list[dict[str, Any]] = []
    # ev1: operational numeric snapshot
    out.append(
        {
            "evidence_id": f"{qid}_ev1",
            "source_type": "log",
            "source_id": "reports/xai_contract_daily_gate_log.jsonl",
            "claim_type": "FACT",
            "evidence_text": (
                "최근 게이트 누적 지표: "
                f"total_runs={metrics['total_runs']}, hold_runs={metrics['hold_runs']}, "
                f"warning_runs={metrics['warning_runs']}, critical_runs={metrics['critical_runs']}, "
                f"pass_rate_mean={metrics['pass_rate_mean']}."
            ),
            "confidence_0_1": 0.95,
            "relation_to_conclusion": "supports",
        }
    )
    # ev2: current failure volume
    out.append(
        {
            "evidence_id": f"{qid}_ev2",
            "source_type": "artifact",
            "source_id": "docs/final/artifacts/xai_contract_failures_latest.json",
            "claim_type": "FACT",
            "evidence_text": f"현재 계약 실패 문항 수는 fail_count={metrics['fail_count']}이다.",
            "confidence_0_1": 0.95,
            "relation_to_conclusion": "supports",
        }
    )
    # ev3: artifact availability context
    for i, ref in enumerate(refs[:3], start=1):
        if i < 3:
            continue
        abs_path = ROOT / ref["path"]
        present = _exists(abs_path)
        claim_type = "FACT" if present else "HYPO"
        confidence = 0.85 if present else 0.4
        text = (
            f"{ref['path']} 존재가 확인되어 운영 근거로 사용 가능하다."
            if present
            else f"{ref['path']} 부재 또는 최신성 이슈 가능성이 있어 보조 가설로 처리한다."
        )
        out.append(
            {
                "evidence_id": f"{qid}_ev3",
                "source_type": "artifact",
                "source_id": ref["path"],
                "claim_type": claim_type,
                "evidence_text": text,
                "confidence_0_1": confidence,
                "relation_to_conclusion": "context",
            }
        )
        break
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template-json", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()

    template = _load(ns.template_json)
    questions = template.get("questions") if isinstance(template.get("questions"), list) else []
    metrics = _metrics_snapshot()

    answers: list[dict[str, Any]] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        qid = str(q.get("question_id") or "unknown")
        qtext = str(q.get("text") or "")
        dtag = str(q.get("domain_tag") or "general")
        evidence = _build_evidence_triplet(qid, metrics)
        answers.append(
            {
                "question_id": qid,
                "question_text": qtext,
                "domain_tag": dtag,
                "decision_trace_id": f"trace_{qid}_artifact_adapter",
                "conclusion_one_line": f"{dtag} 관점에서 현재 우선 과제는 근거 기반 계약 준수 일관성 유지다.",
                "evidence": evidence,
                "limitation_one": "지표는 운영 로그 집계 기반이며 원인 인과는 추가 도메인 분석이 필요하다.",
                "action_guide_one": "해당 도메인 실패 사례를 우선 검토하고 다음 주기 재평가를 실행한다.",
                "review_note": "artifact_adapter_v2_numeric_evidence",
            }
        )

    out = {
        "schema": "xai_runtime_answers_v1",
        "generated_at_utc": _utc_now(),
        "source": "artifact_adapter_v1",
        "answers": answers,
    }
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(ns.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
