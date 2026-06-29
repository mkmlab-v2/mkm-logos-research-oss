#!/usr/bin/env python3
"""Validate WTT pilot session JSONL — schema + masked PII scan ([HYPO])."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/wtt_pilot_session_v1.schema.json"
DEFAULT_OUT = ROOT / "reports/wtt_pilot_jsonl_validate_v1_latest.json"

# Unmasked PII patterns — masked forms (****, █, * in names) should NOT match.
PII_FAIL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("phone_unmasked_kr", re.compile(r"010[-\s]?\d{4}[-\s]?\d{4}")),
    ("phone_unmasked_kr_no_dash", re.compile(r"(?<!\*)\b010\d{8}\b")),
    ("rrn_like", re.compile(r"\b\d{6}[-\s]?\d{7}\b")),
    ("email_unmasked", re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.com)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("credit_card_like", re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")),
]

# Warn-only (human gate display); does not fail --strict validate.
_KOREAN_SURNAMES = "이김박최정윤장임한오서신권황안송류전홍고문양손배조백허유남심노하곽성차주우구나전민진지엄채원천방공강현함변염양여추소석선설마길주연표명기반"
PII_WARN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "korean_name_unmasked",
        re.compile(rf"(?<![가-힣*█])([{_KOREAN_SURNAMES}][가-힣]{{1,2}})(?![가-힣*█])"),
    ),
]

REQUIRED_LABELS_SYNTHETIC = {"masked", "not_customer_data"}
OPERATOR_PANEL_LABELS = frozenset({"operator_panel", "internal_dogfood"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def scan_pii_in_text(text: str) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for name, pat in PII_FAIL_PATTERNS:
        m = pat.search(text)
        if m:
            # Allow if match contains masking asterisks in phone segment
            frag = m.group(0)
            if "****" in frag or "██" in frag:
                continue
            hits.append({"rule": name, "fragment": frag[:32]})
    return hits


def scan_pii_warn_in_text(text: str) -> list[dict[str, str]]:
    """Non-blocking PII hints for human review (e.g. unmasked Korean name tokens)."""
    hits: list[dict[str, str]] = []
    for name, pat in PII_WARN_PATTERNS:
        for m in pat.finditer(text):
            frag = m.group(1) if m.lastindex else m.group(0)
            start = m.start(1) if m.lastindex else m.start(0)
            end = m.end(1) if m.lastindex else m.end(0)
            window = text[max(0, start - 1) : min(len(text), end + 1)]
            if "*" in frag or "█" in frag or "*" in window or "█" in window:
                continue
            if len(frag) < 2:
                continue
            hits.append({"rule": name, "fragment": frag[:32], "severity": "warn"})
    return hits


def validate_session_row(
    row: dict[str, Any],
    *,
    schema: dict[str, Any],
    line_no: int,
    require_synthetic_labels: bool,
    lane_operator_panel: bool = False,
) -> list[dict[str, Any]]:
    import jsonschema

    issues: list[dict[str, Any]] = []
    try:
        jsonschema.validate(row, schema)
    except jsonschema.ValidationError as exc:
        issues.append({"line": line_no, "code": "schema", "message": exc.message})
        return issues

    labels = set(row.get("labels") or [])
    if require_synthetic_labels and not REQUIRED_LABELS_SYNTHETIC.issubset(labels):
        issues.append(
            {
                "line": line_no,
                "code": "labels",
                "message": f"missing required labels {REQUIRED_LABELS_SYNTHETIC - labels}",
            }
        )

    if row.get("customer_provided") is True and "synthetic_spicy" in labels:
        issues.append(
            {
                "line": line_no,
                "code": "provenance",
                "message": "customer_provided=true conflicts with synthetic_spicy label",
            }
        )

    if lane_operator_panel:
        if not OPERATOR_PANEL_LABELS.issubset(labels):
            issues.append(
                {
                    "line": line_no,
                    "code": "operator_panel_labels",
                    "message": f"missing labels {OPERATOR_PANEL_LABELS - labels}",
                }
            )
        if row.get("customer_provided") is True:
            issues.append(
                {
                    "line": line_no,
                    "code": "operator_panel_provenance",
                    "message": "operator_panel lane requires customer_provided=false",
                }
            )
    elif "operator_panel" in labels and row.get("customer_provided") is True:
        issues.append(
            {
                "line": line_no,
                "code": "operator_panel_provenance",
                "message": "operator_panel label requires customer_provided=false",
            }
        )

    user_turns = 0
    for turn in row.get("turns") or []:
        if turn.get("role") == "user":
            user_turns += 1
            for hit in scan_pii_in_text(turn.get("text", "")):
                issues.append(
                    {
                        "line": line_no,
                        "code": "pii_unmasked",
                        "session_id": row.get("session_id"),
                        **hit,
                    }
                )
    if user_turns == 0:
        issues.append({"line": line_no, "code": "turns", "message": "no user turns"})

    return issues


def validate_jsonl(
    path: Path,
    *,
    schema_path: Path = DEFAULT_SCHEMA,
    min_sessions: int = 20,
    max_sessions: int = 50,
    require_synthetic_labels: bool = True,
    lane_operator_panel: bool = False,
) -> dict[str, Any]:
    schema = _load_json(schema_path)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    all_issues: list[dict[str, Any]] = []

    if len(lines) < min_sessions:
        all_issues.append(
            {
                "line": 0,
                "code": "count",
                "message": f"need>={min_sessions} sessions, got {len(lines)}",
            }
        )
    if len(lines) > max_sessions:
        all_issues.append(
            {
                "line": 0,
                "code": "count",
                "message": f"max {max_sessions} sessions, got {len(lines)}",
            }
        )

    for i, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            all_issues.append({"line": i, "code": "json", "message": str(exc)})
            continue
        all_issues.extend(
            validate_session_row(
                row,
                schema=schema,
                line_no=i,
                require_synthetic_labels=require_synthetic_labels,
                lane_operator_panel=lane_operator_panel,
            )
        )

    ok = len(all_issues) == 0
    return {
        "schema": "wtt_pilot_jsonl_validate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "jsonl_path": _rel_to_root(path),
        "session_count": len(lines),
        "ok": ok,
        "issue_count": len(all_issues),
        "issues": all_issues,
        "send_gate": "HOLD",
        "note_ko": "통과해도 synthetic — 실고객 마스킹 전 SEND 해제 불가",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--min-sessions", type=int, default=20)
    ap.add_argument("--max-sessions", type=int, default=50)
    ap.add_argument("--allow-missing-synthetic-labels", action="store_true")
    ap.add_argument("--lane-operator-panel", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 on validation failure.")
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing file: {args.jsonl}"}))
        return 1

    report = validate_jsonl(
        args.jsonl.resolve(),
        schema_path=args.schema,
        min_sessions=args.min_sessions,
        max_sessions=args.max_sessions,
        require_synthetic_labels=not args.allow_missing_synthetic_labels,
        lane_operator_panel=args.lane_operator_panel,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "sessions": report["session_count"], "issues": report["issue_count"]}))
    if args.strict and not report["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
