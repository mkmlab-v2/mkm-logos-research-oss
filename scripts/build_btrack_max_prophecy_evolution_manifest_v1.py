#!/usr/bin/env python3
"""Build B-track max prophecy evolution manifest (research_only, send_gate HOLD)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/btrack_max_prophecy_evolution_manifest_v1.schema.json"
DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/btrack_max_prophecy_evolution_manifest_v1_latest.json"
MAX_PACK = ROOT / "tests/fixtures/general_prophecy_registry_max_evolution_pack_v1.json"
LIT_REVIEW = ROOT / "docs/research/BTRACK_MAX_PROPHECY_EVOLUTION_LIT_REVIEW_2026-06-26.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(doc: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    schema = _load(SCHEMA_PATH)
    Draft202012Validator(schema).validate(doc)


def _domain_histogram(questions: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for q in questions:
        if not isinstance(q, dict):
            continue
        tags = q.get("domain_tags") or []
        if isinstance(tags, list) and tags:
            c[str(tags[0])] += 1
        else:
            c["untagged"] += 1
    return dict(sorted(c.items()))


def _question_counts(questions: list[dict[str, Any]]) -> dict[str, int]:
    pending = resolved = financial = general = 0
    for q in questions:
        if not isinstance(q, dict):
            continue
        track = q.get("prophecy_track") or "general"
        if track == "financial":
            financial += 1
        else:
            general += 1
        status = ((q.get("resolution") or {}).get("status") or "pending").lower()
        if status == "resolved":
            resolved += 1
        else:
            pending += 1
    return {
        "total": len(questions),
        "pending": pending,
        "resolved": resolved,
        "financial_track": financial,
        "general_track": general,
    }


def build_manifest(*, registry_path: Path) -> dict[str, Any]:
    reg = _load(registry_path) if registry_path.is_file() else {"questions": []}
    questions = [q for q in (reg.get("questions") or []) if isinstance(q, dict)]
    doc: dict[str, Any] = {
        "schema": "btrack_max_prophecy_evolution_manifest_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_mode": "max_b_track",
        "send_gate": "HOLD",
        "boundary_ack": True,
        "lit_review_ref": str(LIT_REVIEW.relative_to(ROOT)).replace("\\", "/"),
        "max_pack_fixture": str(MAX_PACK.relative_to(ROOT)).replace("\\", "/"),
        "domain_histogram": _domain_histogram(questions),
        "question_counts": _question_counts(questions),
        "artifact_pointers": {
            "general_prophecy_registry": str(registry_path.relative_to(ROOT)).replace("\\", "/"),
            "general_prophecy_brier_eval": "docs/final/artifacts/general_prophecy_brier_eval_latest.json",
            "holdout_gate": "docs/final/artifacts/general_prophecy_explainability_holdout_gate_v1_latest.json",
            "holdout_evolution_ablation": "docs/final/artifacts/general_prophecy_holdout_evolution_ablation_latest.json",
            "prophecy_hit_rate_eval": "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
            "btrack_prophecy_score": "docs/final/artifacts/btrack_prophecy_score_latest.json",
            "evolution_health": "docs/final/artifacts/general_prophecy_evolution_health_latest.json",
            "micro_signal_bundle": "docs/final/artifacts/micro_signal_observation_bundle_v1_latest.json",
            "daily_chain_report": "reports/btrack_max_prophecy_evolution_daily_chain_v1_latest.json",
        },
        "chains": [
            "scripts/run_btrack_max_prophecy_evolution_daily_chain_v1.py",
            "scripts/run_general_prophecy_daily_queue_refresh_v1.ps1",
            "scripts/run_btrack_daily_hypothesis_chain.ps1",
        ],
        "evolution_policy": {
            "auto_apply_mode": "parameter_only_via_allowlist",
            "holdout_profile_default": "research",
            "proposal_only_no_auto_apply": True,
        },
    }
    _validate(doc)
    return doc


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    p.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    p.add_argument("--stdout-only", action="store_true")
    ns = p.parse_args()

    if not SCHEMA_PATH.is_file():
        print(f"missing schema: {SCHEMA_PATH}", file=sys.stderr)
        return 2

    doc = build_manifest(registry_path=ns.registry)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if ns.stdout_only:
        print(payload, end="")
        return 0
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(ns.output), "questions": doc["question_counts"]["total"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
