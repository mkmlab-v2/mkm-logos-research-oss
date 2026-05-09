#!/usr/bin/env python3
"""Validate MKM Control-Integrity Golden Set v1 JSONL."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSONL = WORKSPACE_ROOT / "scripts" / "data" / "mkm_control_integrity_golden_set_v1_sample10.jsonl"
DEFAULT_SCHEMA = WORKSPACE_ROOT / "docs" / "final" / "schemas" / "mkm_control_integrity_golden_set_v1.schema.json"
DEFAULT_REPORT = WORKSPACE_ROOT / "reports" / "mkm_control_integrity_golden_set_v1_validation_latest.json"


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _try_jsonschema_validate(row: dict[str, Any], schema: dict[str, Any]) -> str | None:
    try:
        import jsonschema  # type: ignore
    except Exception:
        return None
    try:
        jsonschema.validate(row, schema)
    except Exception as exc:  # pragma: no cover
        return str(exc)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate MKM control-integrity golden set JSONL")
    ap.add_argument("--in", dest="input_path", default=str(DEFAULT_JSONL), help="Input JSONL path")
    ap.add_argument("--schema", dest="schema_path", default=str(DEFAULT_SCHEMA), help="Schema JSON path")
    ap.add_argument("--report-out", dest="report_out", default=str(DEFAULT_REPORT), help="Validation report JSON output")
    args = ap.parse_args()

    input_path = _as_abs(args.input_path)
    schema_path = _as_abs(args.schema_path)
    report_out = _as_abs(args.report_out)

    if not input_path.is_file():
        print(f"input not found: {input_path}")
        return 1
    if not schema_path.is_file():
        print(f"schema not found: {schema_path}")
        return 1

    schema = _load_json(schema_path)
    ids: set[str] = set()
    errors: list[str] = []
    split_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    risk_counter: Counter[str] = Counter()
    total = 0

    with input_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                row: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_no}: invalid json: {exc}")
                continue

            sid = str(row.get("sample_id", ""))
            if sid in ids:
                errors.append(f"line {line_no}: duplicate sample_id {sid}")
            else:
                ids.add(sid)

            for field in ("must_include", "must_not_include", "policy_tags"):
                if not isinstance(row.get(field), list):
                    errors.append(f"line {line_no}: {field} must be a list")

            profile = row.get("scoring_profile", {})
            if isinstance(profile, dict):
                fw = float(profile.get("faithfulness_weight", 0))
                sw = float(profile.get("safety_weight", 0))
                tw = float(profile.get("style_weight", 0))
                if abs((fw + sw + tw) - 1.0) > 0.02:
                    errors.append(f"line {line_no}: scoring weights must sum to ~1.0 (got {fw+sw+tw:.3f})")
            else:
                errors.append(f"line {line_no}: scoring_profile must be object")

            schema_err = _try_jsonschema_validate(row, schema)
            if schema_err:
                errors.append(f"line {line_no}: schema error: {schema_err}")

            split_counter[str(row.get("split", "unknown"))] += 1
            domain_counter[str(row.get("domain", "unknown"))] += 1
            risk_counter[str(row.get("risk_level", "unknown"))] += 1

    report = {
        "schema": "mkm_control_integrity_golden_set_v1_validation_report",
        "input": str(input_path),
        "schema_path": str(schema_path),
        "total_rows": total,
        "errors": errors,
        "ok": len(errors) == 0,
        "distribution": {
            "split": dict(split_counter),
            "domain": dict(domain_counter),
            "risk_level": dict(risk_counter),
        },
    }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    with report_out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"rows={total}")
    print(f"errors={len(errors)}")
    print(f"report={report_out}")
    return 0 if len(errors) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
