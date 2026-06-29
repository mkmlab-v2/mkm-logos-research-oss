#!/usr/bin/env python3
"""Promote T3 rubric drafts into civilization apocalypse registry fixture (B-track only)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "tests/fixtures/general_prophecy_registry_civilization_apocalypse_v1.json"
DRAFT = ROOT / "tests/fixtures/civilization_apocalypse_t3_rubric_draft_v1.json"
T3_PTR = ROOT / "tests/fixtures/civilization_apocalypse_layer3_t3_pointers_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    draft = json.loads(DRAFT.read_text(encoding="utf-8"))
    t3_ptr = json.loads(T3_PTR.read_text(encoding="utf-8"))

    existing_ids = {q["question_id"] for q in reg.get("questions") or []}
    new_qs: list[dict] = []
    for item in draft.get("rubric_drafts") or []:
        d = item.get("rubric_draft") or {}
        qid = d.get("proposed_question_id")
        if not qid or qid in existing_ids:
            continue
        slug = qid.split(".")[-1]
        new_qs.append(
            {
                "schema": "general_prophecy_question_v1",
                "research_rail": "B",
                "boundary_ack": True,
                "question_id": qid,
                "question_text": d["proposed_question_text"],
                "domain_tags": ["civilization", "eschatology", "t3"],
                "prophecy_track": "general",
                "resolution_deadline_utc": d["proposed_resolution_deadline_utc"],
                "resolution_criteria": d["proposed_resolution_criteria"],
                "outcome_spec": {
                    "kind": "binary",
                    "true_label": f"{slug}_yes",
                    "false_label": f"{slug}_no",
                },
                "forecasts": [
                    {
                        "issued_at_utc": _utc_now(),
                        "probability_0_1": d["draft_probability_0_1"],
                        "source_kind": "other",
                        "source_detail": "structural_prior_apocalypse_v3_t3_2100_promoted",
                        "brier_ready": True,
                    }
                ],
                "resolution": {"status": "pending"},
                "layer3_interpretation_ref": d["layer3_interpretation_ref"],
                "epistemic_firewall": {
                    "l1_probability_fields": ["forecasts[].probability_0_1"],
                    "l3_narrative_forbidden_in": ["forecasts", "resolution"],
                },
            }
        )

    reg["questions"] = (reg.get("questions") or []) + new_qs
    reg["git_commit_hint"] = (
        "fixture:civilization_apocalypse_v1_t1_12q+t2_8q+t3_4q=24q; "
        "regime_speculative_long_term_extrapolation"
    )
    reg["generated_at_utc"] = _utc_now()
    REG.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    draft["note"] = "promoted_to_registry_fixture_2026-06-07_commander_ordered"
    for item in draft.get("rubric_drafts") or []:
        rd = item.get("rubric_draft") or {}
        rd["promotion_status"] = "promoted_to_civilization_registry_fixture"
    DRAFT.write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for p in t3_ptr.get("t3_pointers") or []:
        p["resolution_rubric"] = "promoted_as_general_prophecy_question_v1_in_registry_fixture"
        p["brier_ready"] = True
    T3_PTR.write_text(json.dumps(t3_ptr, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"added={len(new_qs)} total={len(reg['questions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
