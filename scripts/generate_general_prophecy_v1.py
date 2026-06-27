#!/usr/bin/env python3
"""General prophecy registry pass-through + optional stub forecasts (B rail only).

Validates payload against docs/final/GENERAL_PROPHECY_SCHEMA_V1.json, refreshes
generated_at_utc, optionally appends baseline forecasts for empty slots.

Does not call external APIs (Polymarket, etc.). See CONSTITUTION Prophecy section.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "final" / "GENERAL_PROPHECY_SCHEMA_V1.json"
DEFAULT_IN = ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
# Appended after primary `-i` when `--no-default-merge` is not set (dedupe by question_id; first wins).
DEFAULT_MERGE_PATHS: tuple[Path, ...] = (
    ROOT / "tests" / "fixtures" / "general_prophecy_registry_seed_5_v1.json",
    ROOT / "tests" / "fixtures" / "general_prophecy_registry_brier_smoke_v1.json",
    ROOT / "tests" / "fixtures" / "general_prophecy_registry_live_resolved_bootstrap_v1.json",
    ROOT / "tests" / "fixtures" / "general_prophecy_registry_macro_h2_2026_pack_v1.json",
    ROOT / "tests" / "fixtures" / "general_prophecy_registry_multidomain_seed_v1.json",
    ROOT / "tests" / "fixtures" / "general_prophecy_registry_max_evolution_pack_v1.json",
    ROOT / "tests" / "fixtures" / "general_prophecy_registry_daily_hero_board_v1.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(doc: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:  # pragma: no cover
        raise SystemExit("jsonschema required: pip install jsonschema") from e
    schema = _load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(doc)


def _question_ids(doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for q in doc.get("questions") or []:
        if isinstance(q, dict) and isinstance(q.get("question_id"), str):
            out.add(q["question_id"])
    return out


def _merge_registries(doc: dict[str, Any], paths: list[Path]) -> None:
    """Append questions from other registries; skip duplicate question_id (first wins)."""
    seen = _question_ids(doc)
    qs = doc.get("questions")
    if not isinstance(qs, list):
        qs = []
        doc["questions"] = qs
    for path in paths:
        if not path.is_file():
            raise SystemExit(f"missing merge-from: {path}")
        other = _load_json(path)
        if other.get("schema") != "general_prophecy_registry_v1":
            raise SystemExit(f"merge-from not a registry: {path}")
        rail = doc.get("research_rail")
        if rail and other.get("research_rail") and other.get("research_rail") != rail:
            raise SystemExit(f"research_rail mismatch vs primary: {path}")
        for q in other.get("questions") or []:
            if not isinstance(q, dict):
                continue
            qid = q.get("question_id")
            if not isinstance(qid, str) or qid in seen:
                continue
            seen.add(qid)
            qs.append(q)


def _stub_forecasts(doc: dict[str, Any]) -> None:
    if doc.get("schema") != "general_prophecy_registry_v1":
        return
    now = _utc_now()
    for q in doc.get("questions") or []:
        if not isinstance(q, dict):
            continue
        fc = q.get("forecasts")
        if isinstance(fc, list) and len(fc) > 0:
            continue
        q["forecasts"] = [
            {
                "issued_at_utc": now,
                "probability_0_1": 0.5,
                "source_kind": "baseline",
                "source_detail": "generate_general_prophecy_v1_stub",
                "brier_ready": True,
            }
        ]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", "-i", type=Path, default=DEFAULT_IN, help="Registry JSON")
    p.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT, help="Output path")
    p.add_argument(
        "--merge-from",
        type=Path,
        action="append",
        default=[],
        metavar="PATH",
        help="Additional registry JSON; questions appended after primary (dedupe by question_id).",
    )
    p.add_argument(
        "--no-default-merge",
        action="store_true",
        help=f"Do not auto-merge {', '.join(p.name for p in DEFAULT_MERGE_PATHS)}",
    )
    p.add_argument(
        "--stub-forecasts",
        action="store_true",
        help="Append baseline 0.5 forecast when forecasts[] empty",
    )
    p.add_argument("--dry-run", action="store_true", help="Validate only; no write")
    p.add_argument("--stdout-only", action="store_true", help="Print JSON; no file write")
    ns = p.parse_args()

    if not SCHEMA_PATH.is_file():
        print(f"missing schema: {SCHEMA_PATH}", file=sys.stderr)
        return 2
    if not ns.input.is_file():
        print(f"missing input: {ns.input}", file=sys.stderr)
        return 2

    doc = _load_json(ns.input)
    merge_paths: list[Path] = list(ns.merge_from)
    if not ns.no_default_merge:
        for p in DEFAULT_MERGE_PATHS:
            if p.is_file() and p not in merge_paths:
                merge_paths.append(p)
    if merge_paths:
        _merge_registries(doc, merge_paths)
    if ns.stub_forecasts:
        _stub_forecasts(doc)
    doc["generated_at_utc"] = _utc_now()
    _validate(doc)

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if ns.dry_run:
        print("ok", doc.get("schema"), len(doc.get("questions") or []))
        return 0
    if ns.stdout_only:
        sys.stdout.write(text)
        return 0
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(text, encoding="utf-8")
    print(str(ns.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
