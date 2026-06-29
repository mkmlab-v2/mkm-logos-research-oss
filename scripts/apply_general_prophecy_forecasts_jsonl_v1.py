#!/usr/bin/env python3
"""Apply Layer-1 forecast injections from JSONL into general_prophecy registry (B rail).

JSONL row schema general_prophecy_forecast_inject_row_v1:
  {
    "schema": "general_prophecy_forecast_inject_row_v1",
    "question_id": "max.fx....",
    "forecasts": [ { issued_at_utc, probability_0_1, source_kind, source_detail, brier_ready } ],
    "mode": "append" | "replace_matching_detail_prefix"
  }
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json"
DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
ROW_SCHEMA = "general_prophecy_forecast_inject_row_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_registry(doc: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    schema = _load(SCHEMA_PATH)
    Draft202012Validator(schema).validate(doc)


def _index(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for q in doc.get("questions") or []:
        if isinstance(q, dict) and isinstance(q.get("question_id"), str):
            out[q["question_id"]] = q
    return out


def apply_rows(
    doc: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    default_mode: str = "append",
) -> dict[str, int]:
    by_id = _index(doc)
    stats = {"applied": 0, "skipped_unknown": 0, "skipped_bad_row": 0}
    for row in rows:
        if row.get("schema") != ROW_SCHEMA:
            stats["skipped_bad_row"] += 1
            continue
        qid = row.get("question_id")
        forecasts = row.get("forecasts")
        if not isinstance(qid, str) or not isinstance(forecasts, list) or not forecasts:
            stats["skipped_bad_row"] += 1
            continue
        q = by_id.get(qid)
        if q is None:
            stats["skipped_unknown"] += 1
            continue
        mode = str(row.get("mode") or default_mode)
        existing = q.get("forecasts")
        if not isinstance(existing, list):
            existing = []
        if mode == "replace_matching_detail_prefix":
            prefix = str(row.get("detail_prefix") or forecasts[0].get("source_detail", "")).split(":")[0]
            existing = [
                f
                for f in existing
                if not (isinstance(f, dict) and str(f.get("source_detail", "")).startswith(prefix))
            ]
        q["forecasts"] = existing + [f for f in forecasts if isinstance(f, dict)]
        stats["applied"] += 1
    return stats


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"invalid jsonl line {i} in {path}: {e}") from e
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--output", "-o", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()

    if not ns.jsonl.is_file():
        print(f"missing jsonl: {ns.jsonl}", file=sys.stderr)
        return 2
    if not ns.registry.is_file():
        print(f"missing registry: {ns.registry}", file=sys.stderr)
        return 2

    doc = _load(ns.registry)
    stats = apply_rows(doc, load_jsonl(ns.jsonl))
    doc["generated_at_utc"] = _utc()
    _validate_registry(doc)

    if ns.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, **stats}))
        return 0

    out = ns.output or ns.registry
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), **stats}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
