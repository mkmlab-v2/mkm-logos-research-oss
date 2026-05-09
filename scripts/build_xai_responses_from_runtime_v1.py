#!/usr/bin/env python3
"""Build xai_sample_20_eval_responses_v1 from runtime answer payloads.

Accepted input formats:
1) xai_runtime_answers_v1:
   {
     "schema": "xai_runtime_answers_v1",
     "answers": [
       {
         "question_id": "q01",
         "question_text": "...",
         "domain_tag": "conversion",
         "conclusion_one_line": "...",
         "evidence": [{...}],
         "limitation_one": "...",
         "action_guide_one": "...",
         "review_note": "..."
       }
     ]
   }

2) xai_sample_20_eval_responses_v1 passthrough:
   - Normalizes and re-writes evaluation flags.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "xai_runtime_answers_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "xai_sample_20_eval_responses_latest.json"
SCHEMA_OUT = "xai_sample_20_eval_responses_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_evidence(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for i, ev in enumerate(raw, start=1):
        if not isinstance(ev, dict):
            continue
        claim_type = ev.get("claim_type")
        if claim_type not in ("FACT", "HYPO"):
            claim_type = "HYPO"
        conf = ev.get("confidence_0_1")
        try:
            conf_f = float(conf)
        except Exception:
            conf_f = 0.5
        conf_f = max(0.0, min(1.0, conf_f))
        source_type = str(ev.get("source_type") or "other")
        if source_type not in ("internal_doc", "artifact", "log", "external_article", "other"):
            source_type = "other"
        relation = str(ev.get("relation_to_conclusion") or "context")
        if relation not in ("supports", "contradicts", "context"):
            relation = "context"
        out.append(
            {
                "evidence_id": str(ev.get("evidence_id") or f"ev{i}"),
                "source_type": source_type,
                "source_id": str(ev.get("source_id") or "unknown_source"),
                "claim_type": claim_type,
                "evidence_text": str(ev.get("evidence_text") or "").strip(),
                "confidence_0_1": conf_f,
                "relation_to_conclusion": relation,
            }
        )
    return out


def _to_contract_row_from_runtime(ans: dict[str, Any]) -> dict[str, Any]:
    qid = str(ans.get("question_id") or "").strip()
    qtext = str(ans.get("question_text") or "").strip()
    dtag = str(ans.get("domain_tag") or "general").strip()
    conclusion = str(ans.get("conclusion_one_line") or "").strip()
    limitation = str(ans.get("limitation_one") or "").strip()
    action = str(ans.get("action_guide_one") or "").strip()
    evidence = _ensure_evidence(ans.get("evidence"))

    row = {
        "schema": "xai_decision_trace_contract_v1",
        "version": "v1",
        "decision_trace_id": str(ans.get("decision_trace_id") or f"trace_{qid or 'unknown'}"),
        "question": {
            "question_id": qid,
            "text": qtext,
            "domain_tag": dtag,
        },
        "final_output": {"conclusion_one_line": conclusion},
        "evidence": evidence,
        "limitation": {"limitation_one": limitation},
        "action_guide": {"action_guide_one": action},
        "evaluation": {
            "evidence_count_ok": len(evidence) >= 3,
            "has_limitation": bool(limitation),
            "has_action_guide": bool(action),
            "contract_pass": bool(conclusion) and len(evidence) >= 3 and bool(limitation) and bool(action),
            "review_note": str(ans.get("review_note") or "runtime_mapped_v1"),
        },
    }
    return row


def _normalize_existing_contract_row(row: dict[str, Any]) -> dict[str, Any]:
    q = row.get("question") if isinstance(row.get("question"), dict) else {}
    result = _to_contract_row_from_runtime(
        {
            "question_id": q.get("question_id"),
            "question_text": q.get("text"),
            "domain_tag": q.get("domain_tag"),
            "decision_trace_id": row.get("decision_trace_id"),
            "conclusion_one_line": ((row.get("final_output") or {}).get("conclusion_one_line") if isinstance(row.get("final_output"), dict) else ""),
            "evidence": row.get("evidence"),
            "limitation_one": ((row.get("limitation") or {}).get("limitation_one") if isinstance(row.get("limitation"), dict) else ""),
            "action_guide_one": ((row.get("action_guide") or {}).get("action_guide_one") if isinstance(row.get("action_guide"), dict) else ""),
            "review_note": ((row.get("evaluation") or {}).get("review_note") if isinstance(row.get("evaluation"), dict) else "contract_normalized_v1"),
        }
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()

    if not ns.input.is_file():
        print(f"missing_input: {ns.input}", file=sys.stderr)
        return 2

    doc = _load(ns.input)
    schema = str(doc.get("schema") or "")
    rows: list[dict[str, Any]] = []

    if schema == "xai_runtime_answers_v1":
        answers = doc.get("answers")
        if not isinstance(answers, list):
            print("invalid_input: answers must be list", file=sys.stderr)
            return 2
        for a in answers:
            if isinstance(a, dict):
                rows.append(_to_contract_row_from_runtime(a))
    elif schema == "xai_sample_20_eval_responses_v1":
        answers = doc.get("responses")
        if not isinstance(answers, list):
            print("invalid_input: responses must be list", file=sys.stderr)
            return 2
        for a in answers:
            if isinstance(a, dict):
                rows.append(_normalize_existing_contract_row(a))
    else:
        print("invalid_input_schema: expected xai_runtime_answers_v1 or xai_sample_20_eval_responses_v1", file=sys.stderr)
        return 2

    out = {
        "schema": SCHEMA_OUT,
        "version": "v1",
        "generated_at_utc": _utc_now(),
        "source_runtime_path": _norm(ns.input),
        "responses": rows,
    }
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(ns.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
