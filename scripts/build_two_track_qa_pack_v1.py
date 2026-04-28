#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def build_audience_answer(audience: str, question_id: str) -> str:
    answers = {
        "investor": {
            "q1": "Survivor selection, falsification gate, and rollback policy bound downside before promotion.",
            "q2": "Signals remain research_only until fail-boundary and publication gates pass with evidence.",
            "q3": "We show with/without comparisons and disclose boundary breakpoints for risk context.",
            "q4": "Every claim ties to artifact snapshots and gate state, not narrative-only interpretation.",
            "q5": "When gate posture weakens, promotion is blocked and rollback semantics apply immediately.",
        },
        "policy": {
            "q1": "We require explicit gates and rollback semantics before any claim leaves research lane.",
            "q2": "Evidence fields are mandatory per answer, enabling audit trails and repeatable review.",
            "q3": "Public-safe disclosure redacts proprietary formulas while preserving verifiable governance facts.",
            "q4": "Fail-boundary reports define where confidence degrades and when action must stop.",
            "q5": "Policy-facing outputs remain non-trigger and document reasons for every go/no-go call.",
        },
        "technical": {
            "q1": "Overfitting is constrained by survivor filters plus falsification sensitivity and rollback gates.",
            "q2": "Ablation reports quantify incremental contribution from symbolic and 4D coupling layers.",
            "q3": "All outputs are reproducible JSON artifacts with deterministic scripts and tracked schema.",
            "q4": "Gate_eval fields provide machine-readable execution posture for downstream automation.",
            "q5": "Track separation enforces K-lane insight generation without direct trading trigger coupling.",
        },
    }
    group = answers.get(audience, answers["technical"])
    return group.get(question_id, "Evidence-backed governance controls the output scope.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--presenter-notes-json", required=True)
    ap.add_argument("--output-json", required=True)
    args = ap.parse_args()

    input_path = Path(args.presenter_notes_json)
    output_path = Path(args.output_json)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    data = load(input_path)
    notes = list(data.get("notes_180s") or [])

    question_bank = [
        ("q1", "How do you avoid overfitting?"),
        ("q2", "How do you prevent symbolic insights from becoming unsafe trading triggers?"),
        ("q3", "What proves this is not storytelling-only interpretation?"),
        ("q4", "How can reviewers verify the claims quickly?"),
        ("q5", "What happens operationally when confidence drops?"),
    ]

    audience_qna = []
    for note in notes:
        audience = str(note.get("audience", "general"))
        items = []
        for qid, qtext in question_bank:
            items.append(
                {
                    "question_id": qid,
                    "q": qtext,
                    "a": build_audience_answer(audience, qid),
                    "evidence": {
                        "source_artifact": "two_track_falsification_suite_latest.json",
                        "metric_value": "pending",
                        "as_of_utc": now(),
                        "rollback_rule": "if gate fails then rollback",
                        "gate_eval": {
                            "pass": False,
                            "should_trade": False,
                            "rollback": True,
                            "reasons": ["missing_gate"],
                        },
                    },
                }
            )
        audience_qna.append({"audience": audience, "items": items})

    out = {
        "schema": "two_track_qa_pack_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "defense_prompt_policy": {
            "require_evidence_fields": [
                "source_artifact",
                "metric_value",
                "as_of_utc",
                "rollback_rule",
                "gate_eval",
            ]
        },
        "audience_qna": audience_qna,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
