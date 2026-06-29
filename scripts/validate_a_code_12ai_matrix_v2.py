#!/usr/bin/env python3
"""Validate A-code 12AI matrix v2 sandbox artifacts ([HYPO] / RQ-028)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_SCHEMA = ROOT / "experiments/a_code_12ai_v2/specs/a_code_12ai_matrix_v2.schema.json"
MATRIX_EXAMPLE = ROOT / "experiments/a_code_12ai_v2/specs/a_code_12ai_matrix_v2.example.json"
PATHOLOGY_V25 = ROOT / "docs/final/protocols/A_CODE_12AI_CLINICAL_PATHOLOGY_MATRIX_V2_5.json"
EVAL_CONTRACT = ROOT / "experiments/a_code_12ai_v2/specs/a_code_eval_axes_contract_v2.json"
SPEC_MD = ROOT / "docs/final/protocols/A_CODE_12AI_AUTONOMOUS_OPERATING_SPEC_V2.md"

EXPECTED_CELL_IDS = {
    "S1-Igniter",
    "S2-Governor",
    "S3-Auditor",
    "L1-Ideator",
    "L2-Synthesizer",
    "L3-Refactorer",
    "K1-Scout",
    "K2-Oracle",
    "K3-Archivist",
    "M1-Provisioner",
    "M2-Executioner",
    "M3-Gatekeeper",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_matrix_example() -> list[str]:
    errors: list[str] = []
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema package required"]

    schema = _load_json(MATRIX_SCHEMA)
    doc = _load_json(MATRIX_EXAMPLE)
    jsonschema.Draft7Validator(schema).validate(doc)

    cell_ids = {c["cell_id"] for c in doc.get("cells", [])}
    if cell_ids != EXPECTED_CELL_IDS:
        errors.append(f"cell_id set mismatch: missing={EXPECTED_CELL_IDS - cell_ids} extra={cell_ids - EXPECTED_CELL_IDS}")

    phases_per_axis: dict[str, set[str]] = {}
    for cell in doc["cells"]:
        axis = cell["axis"]
        phases_per_axis.setdefault(axis, set()).add(cell["phase"])
    for axis, phases in phases_per_axis.items():
        if phases != {"genesis", "peak", "storage"}:
            errors.append(f"axis {axis} missing phase coverage: {phases}")

    if not doc.get("research_only"):
        errors.append("matrix example must have research_only=true")
    return errors


def validate_pathology_matrix_crossref() -> list[str]:
    errors: list[str] = []
    pathology = _load_json(PATHOLOGY_V25)
    example = _load_json(MATRIX_EXAMPLE)

    p_cells = {c["cell_id"]: c for c in pathology.get("cells", [])}
    e_cells = {c["cell_id"]: c for c in example.get("cells", [])}

    if set(p_cells) != set(e_cells):
        errors.append("pathology v2.5 cell_id set != matrix example cell_id set")

    for cid in EXPECTED_CELL_IDS:
        if p_cells[cid]["axis"] != e_cells[cid]["axis"]:
            errors.append(f"{cid}: axis mismatch pathology vs example")
        if p_cells[cid]["phase"] != e_cells[cid]["phase"]:
            errors.append(f"{cid}: phase mismatch pathology vs example")

    if pathology.get("hypothesis_tier") != "B" or not pathology.get("research_only"):
        errors.append("pathology matrix must be B-track research_only")

    return errors


def validate_eval_contract() -> list[str]:
    errors: list[str] = []
    contract = _load_json(EVAL_CONTRACT)
    if contract.get("rq_id") != "RQ-028":
        errors.append("eval contract rq_id must be RQ-028")
    forbidden = set(contract.get("forbidden_metric_keys") or [])
    if "price_directional_hit_rate" not in forbidden:
        errors.append("eval contract missing price_directional_hit_rate forbidden key")
    return errors


def validate_ssot_files_exist() -> list[str]:
    errors: list[str] = []
    for path in (MATRIX_SCHEMA, MATRIX_EXAMPLE, PATHOLOGY_V25, EVAL_CONTRACT, SPEC_MD):
        if not path.is_file():
            errors.append(f"missing SSOT file: {path.relative_to(ROOT)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate A-code 12AI v2 sandbox")
    parser.add_argument("--json-out", type=Path, default=None, help="Optional report JSON path")
    args = parser.parse_args()

    checks = {
        "ssot_files_exist": validate_ssot_files_exist(),
        "matrix_example_schema": validate_matrix_example(),
        "pathology_crossref": validate_pathology_matrix_crossref(),
        "eval_contract": validate_eval_contract(),
    }

    all_errors: list[str] = []
    for name, errs in checks.items():
        all_errors.extend([f"{name}: {e}" for e in errs])

    report = {
        "schema": "a_code_12ai_matrix_v2_validation_report_v1",
        "version": "1.0.0",
        "research_only": True,
        "hypothesis_tier": "B",
        "rq_id": "RQ-028",
        "ok": len(all_errors) == 0,
        "checks": {k: {"ok": len(v) == 0, "errors": v} for k, v in checks.items()},
        "ssot": {
            "spec_md": str(SPEC_MD.relative_to(ROOT)),
            "pathology_v25": str(PATHOLOGY_V25.relative_to(ROOT)),
            "matrix_example": str(MATRIX_EXAMPLE.relative_to(ROOT)),
        },
    }

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if all_errors:
        for err in all_errors:
            print(err, file=sys.stderr)
        return 1

    print("a_code_12ai_matrix_v2: validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
