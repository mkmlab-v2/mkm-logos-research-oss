#!/usr/bin/env python3
"""Validate Bible topology contributor shard JSON (B-track · Repo #2 prep · no telemetry).

Human-gated topology PR evidence only — not auto-training or Track A promotion.
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

DEFAULT_OUT = ROOT / "reports/bible_topology_contrib_shard_validate_v1_latest.json"
SCHEMA_ID = "bible_topology_shard_v1"
REQUIRED_LABELS = frozenset({"contributor_provided", "research_only", "bible_topology_shard_v1"})
ALLOWED_RELATIONS = frozenset({"cross_ref", "quotation", "parallel", "genealogy"})
ALLOWED_TIERS = frozenset({"A", "B", "C"})
ALLOWED_SLICE_IDS = frozenset(
    {
        "GENESIS_CREATION_WEEK_v1",
        "GENESIS_PATRIARCHS_EARLY_v1",
        "SYNOPTIC_PASSION_WEEK_v1",
        "SYNOPTIC_SERMON_MOUNT_v1",
        "SYNOPTIC_BIRTH_NARRATIVES_v1",
        "SYNOPTIC_GOSPELS_SUBSET_v1",
        "SYNOPTIC_GOSPELS_EXTENDED_v1",
    }
)
TIER_EDGE_BUDGET = {"A": 500, "B": 2000, "C": 70000}
FORBIDDEN_SUBSTRINGS = (
    "c:\\workspace",
    "/workspace/",
    ".env",
    "credentials",
    "dpapi",
    "api_key",
    "bearer ",
    "harrison rainbow",
    "we ship harrison",
)
VERSE_REF_RE = re.compile(r"^[A-Z]{3}\.\d{1,3}\.\d{1,3}$")
FORBIDDEN_METADATA_KEYS = frozenset({"collapsed_combined_score", "universal_root_single_kpi"})


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


def _scan_text_field(text: str, *, field: str, prefix: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for hit in scan_pii_in_text(text):
        issues.append({**prefix, "code": "pii_fail", "field": field, **hit})
    for hit in scan_pii_warn_in_text(text):
        issues.append({**prefix, "code": "pii_warn", "field": field, **hit})
    for hit in _scan_forbidden_paths(text):
        issues.append({**prefix, **hit, "field": field})
    return issues


def validate_edge(edge: dict[str, Any], *, index: int) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    prefix = {"edge_index": index}

    for key in FORBIDDEN_METADATA_KEYS:
        if key in edge:
            issues.append({**prefix, "code": "forbidden_metadata_key", "message": f"forbidden key on edge: {key}"})

    src = edge.get("src_ref")
    dst = edge.get("dst_ref")
    if not isinstance(src, str) or not VERSE_REF_RE.match(src.strip()):
        issues.append({**prefix, "code": "src_ref_invalid", "message": "src_ref must match BOOK.CCC.VVV (uppercase)"})
    if not isinstance(dst, str) or not VERSE_REF_RE.match(dst.strip()):
        issues.append({**prefix, "code": "dst_ref_invalid", "message": "dst_ref must match BOOK.CCC.VVV (uppercase)"})
    elif isinstance(src, str) and src.strip() == dst.strip():
        issues.append({**prefix, "code": "self_loop", "message": "src_ref and dst_ref must differ"})

    relation = edge.get("relation")
    if relation not in ALLOWED_RELATIONS:
        issues.append(
            {
                **prefix,
                "code": "relation_invalid",
                "message": f"relation must be one of {sorted(ALLOWED_RELATIONS)}",
            }
        )

    if edge.get("contributor_provided") is not True:
        issues.append(
            {**prefix, "code": "contributor_provided_required", "message": "contributor_provided must be true"}
        )
    if edge.get("customer_provided") is not False:
        issues.append(
            {**prefix, "code": "customer_provided_forbidden", "message": "customer_provided must be false"}
        )

    note = edge.get("source_note")
    if not isinstance(note, str) or len(note.strip()) < 8:
        issues.append({**prefix, "code": "source_note_required", "message": "source_note min 8 chars"})
    elif isinstance(note, str):
        issues.extend(_scan_text_field(note, field="source_note", prefix=prefix))

    labels_raw = edge.get("labels")
    if labels_raw is not None:
        if not isinstance(labels_raw, list):
            issues.append({**prefix, "code": "labels_type", "message": "edge labels must be array if present"})
        else:
            missing = sorted(REQUIRED_LABELS - {str(x) for x in labels_raw})
            if missing:
                issues.append({**prefix, "code": "labels_missing", "message": f"missing edge labels: {missing}"})

    return issues


def validate_shard(
    doc: dict[str, Any],
    *,
    min_edges: int,
    max_edges: int,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    if doc.get("schema") != SCHEMA_ID:
        issues.append({"code": "schema_invalid", "message": f"schema must be {SCHEMA_ID!r}"})
    if doc.get("research_only") is not True:
        issues.append({"code": "research_only_required", "message": "research_only must be true"})
    if doc.get("send_gate") not in (None, "HOLD"):
        issues.append({"code": "send_gate_invalid", "message": "top-level send_gate must be HOLD or omitted"})

    slice_id = doc.get("slice_id")
    if slice_id not in ALLOWED_SLICE_IDS:
        issues.append(
            {
                "code": "slice_id_invalid",
                "message": f"slice_id must be one of {sorted(ALLOWED_SLICE_IDS)}",
            }
        )

    tier = doc.get("tier")
    if tier not in ALLOWED_TIERS:
        issues.append({"code": "tier_invalid", "message": f"tier must be one of {sorted(ALLOWED_TIERS)}"})

    budget = doc.get("edge_budget_max")
    if tier in TIER_EDGE_BUDGET:
        cap = TIER_EDGE_BUDGET[tier]
        if budget is not None and int(budget) > cap:
            issues.append(
                {"code": "edge_budget_max_exceeds_tier", "message": f"tier {tier} budget max {cap}, got {budget}"}
            )
        if max_edges > cap:
            issues.append(
                {"code": "cli_max_exceeds_tier", "message": f"CLI max_edges {max_edges} exceeds tier {tier} cap {cap}"}
            )

    for key in FORBIDDEN_METADATA_KEYS:
        if key in doc:
            issues.append({"code": "forbidden_metadata_key", "message": f"forbidden top-level key: {key}"})

    labels_raw = doc.get("labels")
    if not isinstance(labels_raw, list):
        issues.append({"code": "labels_required", "message": "top-level labels array required"})
    else:
        missing = sorted(REQUIRED_LABELS - {str(x) for x in labels_raw})
        if missing:
            issues.append({"code": "labels_missing", "message": f"missing top-level labels: {missing}"})

    provenance = doc.get("provenance_ref")
    if not isinstance(provenance, str) or len(provenance.strip()) < 8:
        issues.append({"code": "provenance_ref_required", "message": "provenance_ref min 8 chars required"})

    edges = doc.get("edges")
    if not isinstance(edges, list):
        issues.append({"code": "edges_required", "message": "edges array required"})
        return issues

    n = len(edges)
    if n < min_edges:
        issues.append({"code": "min_edges", "message": f"need at least {min_edges} edges, got {n}"})
    if n > max_edges:
        issues.append({"code": "max_edges", "message": f"at most {max_edges} edges, got {n}"})

    declared = doc.get("edge_count")
    if declared is not None and int(declared) != n:
        issues.append({"code": "edge_count_mismatch", "message": f"edge_count {declared} != len(edges) {n}"})

    seen: set[tuple[str, str, str]] = set()
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            issues.append({"edge_index": i, "code": "edge_type", "message": "edge must be object"})
            continue
        issues.extend(validate_edge(edge, index=i))
        src = str(edge.get("src_ref", "")).strip()
        dst = str(edge.get("dst_ref", "")).strip()
        rel = str(edge.get("relation", ""))
        key = (src, dst, rel)
        rev = (dst, src, rel)
        if key in seen or (rel == "parallel" and rev in seen):
            issues.append({**{"edge_index": i}, "code": "duplicate_edge", "message": f"duplicate edge {key}"})
        seen.add(key)
        if rel == "parallel":
            seen.add(rev)

    return issues


def _validate_path(
    path: Path,
    *,
    min_edges: int,
    max_edges: int,
    strict: bool,
) -> tuple[bool, dict[str, Any], list[dict[str, Any]]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError("root must be object")
    all_issues = validate_shard(doc, min_edges=min_edges, max_edges=max_edges)
    fail_issues = [x for x in all_issues if x.get("code") != "pii_warn"]
    if strict:
        fail_issues = list(all_issues)
    edges = doc.get("edges") if isinstance(doc.get("edges"), list) else []
    ok = len(fail_issues) == 0
    report: dict[str, Any] = {
        "schema": "bible_topology_contrib_shard_validate_v1",
        "generated_at_utc": _utc(),
        "input_json": _rel(path),
        "input_sha256": _sha256_file(path),
        "shard_schema": doc.get("schema"),
        "slice_id": doc.get("slice_id"),
        "tier": doc.get("tier"),
        "edge_count": len(edges),
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
            "Bible topology shard is B-track PR evidence only; "
            "does not auto-train, bulk-host Harrison graphics, or promote Track A."
        ),
        "reproduce": f"py scripts/validate_bible_topology_contrib_shard_v1.py --json {_rel(path)}",
    }
    return ok, report, fail_issues


def _expand_glob(pattern: str) -> list[Path]:
    if any(ch in pattern for ch in "*?[]"):
        return sorted(ROOT.glob(pattern))
    p = Path(pattern)
    if not p.is_absolute():
        p = ROOT / p
    return [p]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, help="Single shard JSON path")
    ap.add_argument("--glob", type=str, help="Glob under repo root, e.g. tests/fixtures/bible_topology/**/*.json")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-edges", type=int, default=3)
    ap.add_argument("--max-edges", type=int, default=50)
    ap.add_argument("--strict", action="store_true", help="Treat pii_warn as failure")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    paths: list[Path] = []
    if args.json:
        paths.append(args.json.resolve())
    if args.glob:
        paths.extend(_expand_glob(args.glob))
    if not paths:
        ap.error("provide --json and/or --glob")

    paths = sorted({p.resolve() for p in paths})
    missing = [p for p in paths if not p.is_file()]
    if missing:
        print(json.dumps({"validation_ok": False, "error": f"missing: {missing[0]}"}), file=sys.stderr)
        return 2

    batch: list[dict[str, Any]] = []
    all_ok = True
    total_issues = 0
    for path in paths:
        try:
            ok, report, fail_issues = _validate_path(
                path,
                min_edges=args.min_edges,
                max_edges=args.max_edges,
                strict=args.strict,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            print(json.dumps({"validation_ok": False, "error": str(exc), "path": _rel(path)}), file=sys.stderr)
            return 1
        batch.append(report)
        all_ok = all_ok and ok
        total_issues += len(fail_issues)

    summary: dict[str, Any] = {
        "validation_ok": all_ok,
        "file_count": len(batch),
        "issue_count": total_issues,
        "files": [{"input_json": r["input_json"], "validation_ok": r["validation_ok"], "edge_count": r["edge_count"]} for r in batch],
    }

    if len(batch) == 1:
        summary["edge_count"] = batch[0]["edge_count"]
        summary["slice_id"] = batch[0].get("slice_id")

    if not args.stdout_only:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        out_doc = batch[0] if len(batch) == 1 else {"schema": "bible_topology_contrib_shard_validate_batch_v1", "files": batch, **summary}
        args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
