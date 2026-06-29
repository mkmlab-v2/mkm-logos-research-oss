#!/usr/bin/env python3
"""Validate Universal Root contributor fixture shard JSON (B-track · no telemetry).

Contributor shards extend the frozen 500-pair bench via PR — not auto-training.
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

DEFAULT_OUT = ROOT / "reports/universal_root_contributor_fixture_validate_v1_latest.json"
CANONICAL_FIXTURE = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"
SCHEMA_ID = "nsm_41k_lexicon_crosswalk_contrib_v1"
REQUIRED_LABELS = frozenset({"contributor_provided", "research_only", "universal_root_fixture_v1"})
FORBIDDEN_SUBSTRINGS = (
    "c:\\workspace",
    "/workspace/",
    ".env",
    "credentials",
    "dpapi",
    "api_key",
    "bearer ",
)
PRIME_EN_RE = re.compile(r"^[a-z][a-z0-9_\-]{0,48}$")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def _scan_forbidden_paths(text: str) -> list[dict[str, str]]:
    low = text.lower()
    hits: list[dict[str, str]] = []
    for needle in FORBIDDEN_SUBSTRINGS:
        if needle in low:
            hits.append({"code": "forbidden_substring", "message": f"contains forbidden fragment: {needle!r}"})
    return hits


def validate_sample(row: dict[str, Any], *, index: int) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    prefix = {"sample_index": index}

    prime = row.get("prime_en")
    if not isinstance(prime, str) or not PRIME_EN_RE.match(prime.strip()):
        issues.append({**prefix, "code": "prime_en_invalid", "message": "prime_en required lowercase ASCII"})
    elif prime != prime.strip():
        issues.append({**prefix, "code": "prime_en_whitespace", "message": "prime_en must not have outer whitespace"})

    tokens = row.get("probe_tokens")
    if not isinstance(tokens, list) or not (1 <= len(tokens) <= 5):
        issues.append({**prefix, "code": "probe_tokens_invalid", "message": "probe_tokens: list of 1-5 strings"})
    else:
        for ti, tok in enumerate(tokens):
            if not isinstance(tok, str) or not tok.strip():
                issues.append(
                    {**prefix, "code": "probe_token_empty", "message": f"probe_tokens[{ti}] must be non-empty string"}
                )
            else:
                for hit in scan_pii_in_text(tok):
                    issues.append({**prefix, "code": "pii_fail", "field": f"probe_tokens[{ti}]", **hit})
                for hit in scan_pii_warn_in_text(tok):
                    issues.append({**prefix, "code": "pii_warn", "field": f"probe_tokens[{ti}]", **hit})
                for hit in _scan_forbidden_paths(tok):
                    issues.append({**prefix, **hit, "field": f"probe_tokens[{ti}]"})

    lang = row.get("lang_probes")
    if lang is not None and not isinstance(lang, dict):
        issues.append({**prefix, "code": "lang_probes_type", "message": "lang_probes must be object if present"})

    if row.get("contributor_provided") is not True:
        issues.append(
            {**prefix, "code": "contributor_provided_required", "message": "contributor_provided must be true"}
        )
    if row.get("customer_provided") is not False:
        issues.append(
            {**prefix, "code": "customer_provided_forbidden", "message": "customer_provided must be false"}
        )

    labels_raw = row.get("labels")
    if not isinstance(labels_raw, list):
        issues.append({**prefix, "code": "labels_required", "message": "labels array required"})
    else:
        labels = {str(x) for x in labels_raw}
        missing = sorted(REQUIRED_LABELS - labels)
        if missing:
            issues.append({**prefix, "code": "labels_missing", "message": f"missing labels: {missing}"})

    note = row.get("source_note")
    if not isinstance(note, str) or len(note.strip()) < 8:
        issues.append({**prefix, "code": "source_note_required", "message": "source_note min 8 chars"})
    elif note:
        for hit in scan_pii_in_text(note):
            issues.append({**prefix, "code": "pii_fail", "field": "source_note", **hit})
        for hit in scan_pii_warn_in_text(note):
            issues.append({**prefix, "code": "pii_warn", "field": "source_note", **hit})
        for hit in _scan_forbidden_paths(note):
            issues.append({**prefix, **hit, "field": "source_note"})

    if row.get("send_gate") not in (None, "HOLD"):
        issues.append({**prefix, "code": "send_gate_invalid", "message": "send_gate must be HOLD or omitted on row"})

    return issues


def validate_shard(doc: dict[str, Any], *, min_rows: int, max_rows: int) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    if doc.get("schema") != SCHEMA_ID:
        issues.append({"code": "schema_invalid", "message": f"schema must be {SCHEMA_ID!r}"})
    if doc.get("send_gate") not in (None, "HOLD"):
        issues.append({"code": "send_gate_invalid", "message": "top-level send_gate must be HOLD or omitted"})
    if doc.get("research_only") is not True:
        issues.append({"code": "research_only_required", "message": "research_only must be true"})

    samples = doc.get("samples")
    if not isinstance(samples, list):
        issues.append({"code": "samples_required", "message": "samples array required"})
        return issues

    n = len(samples)
    if n < min_rows:
        issues.append({"code": "min_rows", "message": f"need at least {min_rows} samples, got {n}"})
    if n > max_rows:
        issues.append({"code": "max_rows", "message": f"at most {max_rows} samples per shard, got {n}"})

    declared = doc.get("pair_count")
    if declared is not None and declared != n:
        issues.append(
            {"code": "pair_count_mismatch", "message": f"pair_count {declared} != len(samples) {n}"}
        )

    for i, row in enumerate(samples):
        if not isinstance(row, dict):
            issues.append({"sample_index": i, "code": "sample_type", "message": "sample must be object"})
            continue
        issues.extend(validate_sample(row, index=i))

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, required=True, dest="json_path")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-rows", type=int, default=3)
    ap.add_argument("--max-rows", type=int, default=50)
    ap.add_argument("--strict", action="store_true", help="Treat pii_warn as failure")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    inp = args.json_path.resolve()
    if not inp.is_file():
        print(json.dumps({"validation_ok": False, "error": f"missing: {inp}"}), file=sys.stderr)
        return 2

    try:
        doc = json.loads(inp.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        print(json.dumps({"validation_ok": False, "error": str(exc)}), file=sys.stderr)
        return 1

    if not isinstance(doc, dict):
        print(json.dumps({"validation_ok": False, "error": "root must be object"}), file=sys.stderr)
        return 1

    all_issues = validate_shard(doc, min_rows=args.min_rows, max_rows=args.max_rows)
    fail_issues = [x for x in all_issues if x.get("code") != "pii_warn"]
    if args.strict:
        fail_issues = list(all_issues)

    samples = doc.get("samples") if isinstance(doc.get("samples"), list) else []
    ok = len(fail_issues) == 0
    report: dict[str, Any] = {
        "schema": "universal_root_contributor_fixture_validate_v1",
        "generated_at_utc": _utc(),
        "input_json": _rel(inp),
        "input_sha256": _sha256_file(inp),
        "shard_schema": doc.get("schema"),
        "sample_count": len(samples),
        "validation_ok": ok,
        "research_only": True,
        "send_gate": "HOLD",
        "auto_track_a_promotion_allowed": False,
        "telemetry": False,
        "issue_count": len(fail_issues),
        "warn_count": sum(1 for x in all_issues if x.get("code") == "pii_warn"),
        "issues": fail_issues[:100],
        "issues_truncated": len(fail_issues) > 100,
        "boundary_ack": (
            "Contributor fixture shard is B-track PR evidence only; "
            "does not auto-train, upload corpora, or promote Track A."
        ),
        "reproduce": f"py scripts/validate_universal_root_contributor_fixture_v1.py --json {_rel(inp)}",
    }

    if not args.stdout_only:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"validation_ok": ok, "sample_count": len(samples), "issues": len(fail_issues)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
