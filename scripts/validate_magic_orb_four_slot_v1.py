#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate magic_orb four_slot_response_v1 — post-build gate for job / panorama payloads."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"

JOB_QUERY_IDS = frozenset({"job_suffering_reason", "job_prologue_suffering"})
JOB_QUERY_RE = re.compile(r"욥|job", re.I)
FORBIDDEN_BADGE_VALUES = frozenset({"Fact-Lock 100%", "fact-lock 100%"})


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_job_context(query: str, query_id: str | None) -> bool:
    if query_id and query_id in JOB_QUERY_IDS:
        return True
    return bool(JOB_QUERY_RE.search(query))


def validate(doc: dict[str, Any], *, require_four_slot_for_job: bool = True) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != "magic_orb_question_insight_v1":
        errors.append("schema must be magic_orb_question_insight_v1")

    query = str(doc.get("query") or "")
    query_id = doc.get("query_id")
    job = _is_job_context(query, str(query_id) if query_id else None)
    four = doc.get("four_slot_response_v1")

    if job and require_four_slot_for_job and not four:
        errors.append("job context requires four_slot_response_v1")
        return errors

    if not four:
        return errors

    if four.get("schema_version") != "four_slot_response_v1":
        errors.append("four_slot_response_v1.schema_version mismatch")

    enf = four.get("enforcement") or {}
    if enf.get("send_gate") != "HOLD":
        errors.append("enforcement.send_gate must be HOLD")
    badge = str(enf.get("badge_ko") or "")
    if badge in FORBIDDEN_BADGE_VALUES:
        errors.append("badge_ko must not use forbidden Fact-Lock 100% copy")

    slots = four.get("slots") or {}
    fact = slots.get("fact_locked") or {}
    fact_items = fact.get("items") or []
    if not fact_items and not fact.get("empty_reason"):
        errors.append("fact_locked empty without empty_reason")

    for key in ("imagination_path", "unknown_gap"):
        for item in (slots.get(key) or {}).get("items") or []:
            if not item.get("must_not_present_as_fact", True):
                errors.append(f"{key} item must_not_present_as_fact must be true")

    for row in doc.get("rag_evidence") or []:
        if not isinstance(row, dict):
            continue
        if "utterance_class" not in row:
            errors.append("rag_evidence row missing utterance_class")
            break
        uclass = row.get("utterance_class")
        if uclass == "imagination_path" and not row.get("must_not_present_as_fact", True):
            errors.append("imagination_path rag row must_not_present_as_fact")
            break

    if job:
        imp = (slots.get("imagination_path") or {}).get("items") or []
        if len(imp) < 2:
            errors.append("job context expects >=2 imagination_path items")
        corpus = (slots.get("corpus_bound") or {}).get("items") or []
        if not corpus:
            errors.append("job context expects >=1 corpus_bound item")

    traj = doc.get("interpretive_trajectory_v1")
    if job and traj:
        if not traj.get("interaction", {}).get("no_merge_to_single_answer"):
            errors.append("interpretive_trajectory must set no_merge_to_single_answer")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate magic orb four_slot payload.")
    ap.add_argument("--insight-json", type=Path, default=DEFAULT_INSIGHT)
    ap.add_argument("--allow-missing-four-slot", action="store_true")
    args = ap.parse_args()

    path = args.insight_json if args.insight_json.is_absolute() else ROOT / args.insight_json
    if not path.is_file():
        print(json.dumps({"ok": False, "error": "missing_insight", "path": str(path)}, ensure_ascii=False))
        return 1

    doc = _load(path)
    errors = validate(doc, require_four_slot_for_job=not args.allow_missing_four_slot)
    out = {"ok": len(errors) == 0, "errors": errors, "path": str(path)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
