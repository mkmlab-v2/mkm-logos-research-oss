#!/usr/bin/env python3
"""Scope stub for 3c: re-export master codebook with frozen other:: policy (no export run)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DIFF = PILOT / "master_codebook_41775_vs_41658_atom_diff_v1.json"
FEAS = PILOT / "master_codebook_other_align_feasibility_v1.json"
POINTER = PILOT / "master_codebook_bench_lexicon_pointer_v1_latest.json"
EXPORT_SCRIPT = ROOT / "scripts" / "export_master_codebook_v1.py"
OUT = PILOT / "master_codebook_3c_reexport_scope_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def main() -> int:
    for p in (DIFF, FEAS, EXPORT_SCRIPT):
        if not p.is_file():
            print(f"ERROR: missing {p}", file=sys.stderr)
            return 2

    diff = json.loads(DIFF.read_text(encoding="utf-8"))
    feas = json.loads(FEAS.read_text(encoding="utf-8"))
    only775 = diff.get("only_in_41775") or []
    only658 = diff.get("only_in_41658") or []

    doc: dict[str, Any] = {
        "schema": "master_codebook_3c_reexport_scope_v1",
        "generated_at_utc": _utc(),
        "status": "scope_only_not_executed",
        "research_only": True,
        "promotion": "HOLD — do not replace production 41658 without human sign-off",
        "preferred_alternative": "3a scoped overlay (12 other:: atoms) already restores 41775 Golden40 KPI",
        "inputs_required": {
            "export_script": _rel(EXPORT_SCRIPT),
            "atoms_jsonl": "reports/constitution/btrack_pilot/original_language_master_atoms_latest.jsonl",
            "lexicon_seed_jsonl": "reports/constitution/btrack_pilot/master_atoms_lexicon_seed_latest.jsonl",
            "morphhb_seed_jsonl": "reports/constitution/btrack_pilot/master_atoms_morphhb_seed_latest.jsonl",
        },
        "diff_summary": {
            "only_in_41775": len(only775),
            "only_in_41658": len(only658),
            "net_row_delta": diff.get("net_row_delta"),
            "greek_hebrew_parity": diff.get("greek_hebrew_parity"),
        },
        "policy_questions_unresolved": [
            "Freeze rule for other:: rows: include all 152, meta-noise filter, or match 3a six-case union only?",
            "Whether re-export overwrites master_codebook_lexicon_v1_41658_rows_latest.json or writes new row_count path",
            "Regression gate: golden40_ab + compression_golden_bench_regression before any production pointer swap",
        ],
        "estimated_steps": [
            "Define other:: export filter spec (JSON schema or script flag)",
            "Run export_master_codebook_v1.py → new lexicon path (e.g. *_41658_other_policy_v1.json)",
            "Run build_master_codebook_golden40_lexicon_ab_v1.py against new path",
            "Run check_compression_golden_bench_regression_v1.py (ACTIVE unchanged)",
            "Update master_codebook_bench_lexicon_pointer only after human sign-off",
        ],
        "risk": "3b-class: full 152-row merge likely reintroduces pipeline/meta tokens (feasibility high_risk)",
        "feasibility_pointer": _rel(FEAS),
        "bench_pointer": _rel(POINTER) if POINTER.is_file() else None,
        "recommendation": "defer_3c_until_3a_promotion_decision; if 089 headline needed use 3a overlay not full reexport",
    }

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
