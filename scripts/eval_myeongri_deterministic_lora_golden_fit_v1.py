#!/usr/bin/env python3
"""Eval: JSONL golden rows schema-fit + Pack 0-B hygiene (no M31 keys, no calculated_at).

Writes ``reports/myeongri_deterministic_lora_golden_fit_latest.json`` (override with ``--out``).
Does **not** run GPU inference — dataset/contract gate only.
Adapter weights SSOT directory is ``adapter_repo_relative`` from profiles (tracked placeholder under ``storage/``; ``models/**`` is gitignored in this repo).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input-jsonl",
        type=Path,
        default=_WS / "tests/fixtures/myeongri_deterministic_lora_golden_sample_v1.jsonl",
    )
    ap.add_argument(
        "--row-schema",
        type=Path,
        default=_WS / "docs/final/schemas/myeongri_deterministic_lora_golden_set_v1.schema.json",
    )
    ap.add_argument(
        "--profiles-json",
        type=Path,
        default=_WS / "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=_WS / "reports/myeongri_deterministic_lora_golden_fit_latest.json",
    )
    args = ap.parse_args()

    try:
        import jsonschema
    except ImportError:
        print("error: jsonschema required", file=sys.stderr)
        return 2

    schema = json.loads(args.row_schema.read_text(encoding="utf-8"))
    profiles = json.loads(args.profiles_json.read_text(encoding="utf-8"))
    adapter_rel = profiles.get("adapter_repo_relative", "")
    if not adapter_rel:
        print("error: profiles missing adapter_repo_relative", file=sys.stderr)
        return 2

    adapter_dir = (_WS / adapter_rel).resolve()
    if not adapter_dir.is_dir():
        print(f"error: adapter_repo_relative not a directory: {adapter_dir}", file=sys.stderr)
        return 5

    lines = [ln for ln in args.input_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    by_split: dict[str, int] = {}
    bad = 0
    forbidden = ("hormone_like", "rag_metabolism", "m31_audit", "gematria_seed_trace")
    blob_lower = "\n".join(lines).lower()
    for fk in forbidden:
        if fk in blob_lower:
            print(f"error: forbidden token in jsonl: {fk}", file=sys.stderr)
            return 3

    for ln in lines:
        row = json.loads(ln)
        try:
            jsonschema.validate(instance=row, schema=schema)
        except jsonschema.ValidationError as e:
            bad += 1
            print(f"schema_error: {e.message}", file=sys.stderr)
        sp = row.get("split", "?")
        by_split[sp] = by_split.get(sp, 0) + 1
        fs = row.get("expected_result", {}).get("full_saju", {})
        if "calculated_at" in fs:
            print("error: calculated_at must not appear in golden full_saju", file=sys.stderr)
            return 4

    if bad:
        return 1

    report = {
        "schema": "myeongri_deterministic_lora_golden_fit_report_v1",
        "generated_at_utc": _utc(),
        "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
        "row_schema": str(args.row_schema).replace("\\", "/"),
        "profiles_ssot": str(args.profiles_json).replace("\\", "/"),
        "adapter_repo_relative_ssot": adapter_rel.replace("\\", "/"),
        "rows_total": len(lines),
        "rows_by_split": by_split,
        "schema_valid_rate": 1.0,
        "no_calculated_at_in_expected": True,
        "forbidden_keys_absent": True,
        "ok": True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
