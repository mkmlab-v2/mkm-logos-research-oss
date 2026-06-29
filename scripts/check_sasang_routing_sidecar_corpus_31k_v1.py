#!/usr/bin/env python3
"""Gate: sasang routing sidecar 31k corpus overlay — manifest + JSONL sample walls."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_sasang_routing_sidecar_on_gematria_path_v1 import evaluate as evaluate_sidecar

DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_manifest_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sasang_routing_sidecar_corpus_31k_gate_v1_latest.json"
EXPECTED_VERSE_COUNT = 31102


def _rel_or_abs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl_line(path: Path, index: int) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8-sig") as f:
        for i, line in enumerate(f):
            if i == index:
                s = line.strip()
                if not s:
                    return None
                doc = json.loads(s)
                return doc if isinstance(doc, dict) else None
    return None


def _count_jsonl_lines(path: Path) -> int:
    n = 0
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def _row_to_sidecar(row: dict[str, Any], *, generated_at_utc: str) -> dict[str, Any]:
    hints = row.get("sasang_routing_hints") or {}
    return {
        "schema": "sasang_routing_sidecar_on_gematria_path_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "path_id": row.get("path_id"),
        "gematria_path_ref": row.get("gematria_path_ref"),
        "sasang_routing_hints": {
            **hints,
            "forbidden_flags": [
                "no_prophecy_vote_merge",
                "no_score_linear_blend",
                "no_constitutional_quadrant_diagnosis",
                "no_track_a_compression_floor",
            ],
        },
        "forbidden_synthesis_ack": True,
        "must_not_merge_into": [
            "prophecy_vote",
            "track_a_compression_floor",
            "production_gematria_kernel",
        ],
    }


def evaluate(manifest: dict[str, Any], *, require_full_corpus: bool) -> tuple[bool, list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    if manifest.get("schema") != "sasang_routing_sidecar_corpus_31k_manifest_v1":
        errors.append("manifest schema mismatch")
    checks.append(
        {
            "kind": "manifest_schema",
            "ok": manifest.get("schema") == "sasang_routing_sidecar_corpus_31k_manifest_v1",
        }
    )

    for flag, expected in (
        ("research_only", True),
        ("non_gating", True),
        ("track_a_blocked", True),
        ("forbidden_synthesis_ack", True),
        ("track_a_promotion", False),
    ):
        ok = manifest.get(flag) is expected
        checks.append({"kind": flag, "ok": ok})
        if not ok:
            errors.append(f"{flag} must be {expected}")

    if str(manifest.get("send_gate", "")).upper() != "HOLD":
        errors.append("send_gate must be HOLD")

    verse_count = int(manifest.get("verse_count") or 0)
    if require_full_corpus and verse_count != EXPECTED_VERSE_COUNT:
        errors.append(f"expected {EXPECTED_VERSE_COUNT} verses, got {verse_count}")

    jsonl_rel = str(manifest.get("jsonl_path") or "")
    jsonl_path = (ROOT / jsonl_rel.replace("/", "\\")) if jsonl_rel and not Path(jsonl_rel).is_absolute() else Path(jsonl_rel)
    if not jsonl_path.is_file():
        errors.append(f"missing jsonl: {jsonl_rel}")
        line_count = 0
    else:
        line_count = _count_jsonl_lines(jsonl_path)
        ok = line_count == verse_count
        checks.append({"kind": "jsonl_line_count", "ok": ok, "lines": line_count, "verse_count": verse_count})
        if not ok:
            errors.append(f"jsonl lines {line_count} != verse_count {verse_count}")

    hist = manifest.get("posture_histogram") or {}
    for key in ("pathology_state", "posture_hint", "entropy_leg"):
        bucket = hist.get(key) or {}
        total = sum(int(v) for v in bucket.values())
        ok = total == verse_count
        checks.append({"kind": f"histogram:{key}", "ok": ok, "total": total})
        if not ok:
            errors.append(f"posture_histogram.{key} sum {total} != verse_count {verse_count}")

    generated_at = str(manifest.get("generated_at_utc") or _utc())
    if jsonl_path.is_file() and verse_count > 0:
        sample_indices = sorted({0, verse_count // 2, verse_count - 1})
        for idx in sample_indices:
            row = _read_jsonl_line(jsonl_path, idx)
            if row is None:
                errors.append(f"missing jsonl row at index {idx}")
                continue
            if row.get("schema") != "sasang_routing_sidecar_corpus_row_v1":
                errors.append(f"row {idx} schema mismatch")
            sidecar = _row_to_sidecar(row, generated_at_utc=generated_at)
            ok, row_errors, _ = evaluate_sidecar(sidecar)
            checks.append({"kind": f"sample_sidecar_gate:{idx}", "ok": ok, "errors": row_errors[:3]})
            if not ok:
                errors.append(f"sample row {idx} failed sidecar gate: {row_errors[:2]}")

    return (not errors), errors, checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--allow-partial", action="store_true", help="smoke: do not require full 31102 count")
    args = ap.parse_args()

    if not args.manifest.is_file():
        print(json.dumps({"ok": False, "error": f"missing manifest: {args.manifest}"}))
        return 1

    manifest = _load(args.manifest)
    ok, errors, checks = evaluate(manifest, require_full_corpus=not args.allow_partial)
    report = {
        "schema": "sasang_routing_sidecar_corpus_31k_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "ok": ok,
        "decision": "PASS" if ok else "FAIL",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "g2_substatus": "corpus_v1_complete" if ok and not args.allow_partial else "pending",
        "input": _rel_or_abs(args.manifest),
        "verse_count": int(manifest.get("verse_count") or 0),
        "errors": errors,
        "checks": checks,
        "reproduce": "py scripts/check_sasang_routing_sidecar_corpus_31k_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "decision": report["decision"], "errors": len(errors)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
