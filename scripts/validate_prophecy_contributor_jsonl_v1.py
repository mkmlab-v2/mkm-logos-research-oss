#!/usr/bin/env python3
"""Validate GitHub/open-bench contributor prophecy JSONL — B-track general prophecy questions.

Forbidden: customer_provided=true, live trading triggers, unmasked PII in rubric text.
Required: contributor_provided=true, research_only label, falsifiable question fields.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_wtt_pilot_jsonl_v1 import scan_pii_in_text, scan_pii_warn_in_text

DEFAULT_OUT = ROOT / "reports/prophecy_contributor_jsonl_validate_v1_latest.json"

REQUIRED_LABELS = frozenset({"contributor_provided", "research_only"})
FORBIDDEN_LABELS = frozenset(
    {
        "operator_panel",
        "synthetic_stub",
        "customer_provided",
        "track_a_promoted",
        "live_trading",
    }
)
QUESTION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
MIN_QUESTION_TEXT = 20


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_row(row: dict[str, Any], *, line_no: int, seen_ids: set[str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    if row.get("schema") not in ("prophecy_contributor_question_v1", "general_prophecy_question_v1"):
        issues.append(
            {
                "line": line_no,
                "code": "schema_invalid",
                "message": "schema must be prophecy_contributor_question_v1 or general_prophecy_question_v1",
            }
        )

    qid = row.get("question_id")
    if not isinstance(qid, str) or not QUESTION_ID_RE.match(qid.strip()):
        issues.append({"line": line_no, "code": "question_id_invalid", "message": "question_id slug required"})
    else:
        if qid in seen_ids:
            issues.append({"line": line_no, "code": "question_id_duplicate", "message": f"duplicate: {qid}"})
        seen_ids.add(qid)

    qtext = row.get("question_text")
    if not isinstance(qtext, str) or len(qtext.strip()) < MIN_QUESTION_TEXT:
        issues.append(
            {
                "line": line_no,
                "code": "question_text_short",
                "message": f"question_text min {MIN_QUESTION_TEXT} chars",
            }
        )
    else:
        for hit in scan_pii_in_text(qtext):
            issues.append({"line": line_no, "code": "pii_fail", **hit})
        for hit in scan_pii_warn_in_text(qtext):
            issues.append({"line": line_no, "code": "pii_warn", **hit})

    rubric = row.get("resolution_criteria")
    if not isinstance(rubric, str) or len(rubric.strip()) < 30:
        issues.append(
            {"line": line_no, "code": "resolution_criteria_short", "message": "resolution_criteria min 30 chars"}
        )

    if not isinstance(row.get("resolution_deadline_utc"), str):
        issues.append({"line": line_no, "code": "resolution_deadline_required", "message": "resolution_deadline_utc required"})

    outcome = row.get("outcome_spec")
    if not isinstance(outcome, dict) or outcome.get("kind") != "binary":
        issues.append({"line": line_no, "code": "outcome_spec_binary", "message": "outcome_spec.kind must be binary"})

    forecasts = row.get("forecasts")
    if not isinstance(forecasts, list) or not forecasts:
        issues.append({"line": line_no, "code": "forecasts_required", "message": "forecasts[] required"})
    else:
        ok_fc = False
        for fc in forecasts:
            if isinstance(fc, dict) and isinstance(fc.get("probability_0_1"), (int, float)):
                ok_fc = True
                break
        if not ok_fc:
            issues.append(
                {"line": line_no, "code": "forecast_probability_missing", "message": "forecasts need probability_0_1"}
            )

    if row.get("customer_provided") is True:
        issues.append(
            {
                "line": line_no,
                "code": "customer_provided_forbidden",
                "message": "contributor lane must set customer_provided=false",
            }
        )

    if row.get("contributor_provided") is not True:
        issues.append(
            {
                "line": line_no,
                "code": "contributor_provided_required",
                "message": "contributor_provided must be true",
            }
        )

    labels_raw = row.get("labels")
    if not isinstance(labels_raw, list):
        issues.append({"line": line_no, "code": "labels_required", "message": "labels array required"})
    else:
        labels = {str(x) for x in labels_raw}
        missing = sorted(REQUIRED_LABELS - labels)
        if missing:
            issues.append(
                {"line": line_no, "code": "labels_missing", "message": f"missing required labels: {missing}"}
            )
        for bad in sorted(labels & FORBIDDEN_LABELS):
            issues.append({"line": line_no, "code": "label_forbidden", "message": f"forbidden label: {bad}"})

    if row.get("research_rail") not in (None, "B", "OBSERVATION_ONLY"):
        issues.append({"line": line_no, "code": "research_rail_invalid", "message": "research_rail must be B or OBSERVATION_ONLY"})

    if row.get("send_gate") not in (None, "HOLD"):
        issues.append({"line": line_no, "code": "send_gate_invalid", "message": "send_gate must be HOLD or omitted"})

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-rows", type=int, default=5)
    ap.add_argument("--strict", action="store_true", help="Treat pii_warn as failure")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    inp = args.jsonl.resolve()
    if not inp.is_file():
        print(f"error: missing jsonl: {inp}", file=sys.stderr)
        return 2

    all_issues: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    row_count = 0
    resolved_count = 0
    for i, line in enumerate(inp.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row_count += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            all_issues.append({"line": i, "code": "json", "message": str(exc)})
            continue
        if not isinstance(row, dict):
            all_issues.append({"line": i, "code": "row_type", "message": "row must be object"})
            continue
        res = row.get("resolution")
        if isinstance(res, dict) and res.get("status") == "resolved":
            resolved_count += 1
        all_issues.extend(validate_row(row, line_no=i, seen_ids=seen_ids))

    fail_issues = [x for x in all_issues if x.get("code") != "pii_warn"]
    if args.strict:
        fail_issues = list(all_issues)

    if row_count < args.min_rows:
        fail_issues.append(
            {
                "line": 0,
                "code": "min_rows",
                "message": f"need at least {args.min_rows} rows, got {row_count}",
            }
        )

    ok = len(fail_issues) == 0
    doc: dict[str, Any] = {
        "schema": "prophecy_contributor_jsonl_validate_v1",
        "generated_at_utc": _utc(),
        "input_jsonl": _rel(inp),
        "input_sha256": _sha256_file(inp),
        "row_count": row_count,
        "resolved_count": resolved_count,
        "validation_ok": ok,
        "lane": "contributor_provided",
        "track": "btrack_research_only",
        "auto_registry_merge_allowed": False,
        "issue_count": len(fail_issues),
        "warn_count": sum(1 for x in all_issues if x.get("code") == "pii_warn"),
        "issues": fail_issues[:100],
        "issues_truncated": len(fail_issues) > 100,
        "boundary_ack": (
            "Contributor prophecy JSONL is B-track bench evidence only; "
            "does not imply customer SLA, SEND, live trading, or Track A price hit-rate headline."
        ),
    }

    if not args.stdout_only:
        out = args.out_json.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"validation_ok": ok, "row_count": row_count, "resolved_count": resolved_count}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
