"""
TKM encounter_sequence_v1 JSONL ledger — validate + append (B-track).

Schema: docs/final/schemas/encounter_sequence_v1.schema.json
Separate from clinic_constitution_mvp ledger and market sasang_dynamics ledger.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

WORKSPACE_DATA_REL = Path("data/clinic")
LEDGER_PREFIX = "encounter_sequence_v1"
SAMPLE_REL = WORKSPACE_DATA_REL / "encounter_sequence_v1.sample.jsonl"
SCHEMA_REL = Path("docs/final/schemas/encounter_sequence_v1.schema.json")


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def _schema_validator():
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema required for encounter_sequence validation") from exc
    root = _workspace_root()
    schema = json.loads((root / SCHEMA_REL).read_text(encoding="utf-8-sig"))
    return jsonschema.Draft7Validator(schema)


def validate_encounter_sequence_record(record: dict[str, Any]) -> list[str]:
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    validator = _schema_validator()
    errors: list[str] = []
    for err in sorted(validator.iter_errors(record), key=lambda e: e.path):
        loc = ".".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{loc}: {err.message}")
    return errors


def append_encounter_sequence_line(
    workspace_root: Path,
    record: dict[str, Any],
    *,
    set_generated_at_if_missing: bool = True,
) -> Path:
    errs = validate_encounter_sequence_record(record)
    if errs:
        raise ValueError("; ".join(errs))
    out_dir = workspace_root / WORKSPACE_DATA_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    daily = out_dir / f"{LEDGER_PREFIX}_{now.strftime('%Y%m%d')}.jsonl"
    payload = dict(record)
    if set_generated_at_if_missing and not str(payload.get("generated_at_utc", "")).strip():
        payload["generated_at_utc"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    with daily.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return daily


def validate_jsonl_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        errs = validate_encounter_sequence_record(obj)
        if errs:
            raise ValueError(f"line {i}: {'; '.join(errs)}")
        n += 1
    return n


def iter_ledger_records(workspace_root: Path, *, glob_pattern: str = "encounter_sequence_v1*.jsonl") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    base = workspace_root / WORKSPACE_DATA_REL
    if not base.is_dir():
        return out
    for path in sorted(base.glob(glob_pattern)):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="TKM encounter_sequence_v1 JSONL ledger (B-track)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate JSONL file")
    p_val.add_argument("--path", type=Path, required=True)

    p_val_sample = sub.add_parser("validate-sample", help="Validate bundled sample JSONL")
    p_val_sample.add_argument("--path", type=Path, default=None)

    p_app = sub.add_parser("append", help="Append one JSON object from stdin or --json")
    p_app.add_argument("--json", type=str, default="")

    args = p.parse_args(argv)
    root = _workspace_root()

    if args.cmd == "validate":
        n = validate_jsonl_file(args.path)
        print(f"OK: {n} line(s) validated: {args.path}")
        return 0

    if args.cmd == "validate-sample":
        path = args.path or (root / SAMPLE_REL)
        n = validate_jsonl_file(path)
        print(f"OK: {n} line(s) validated: {path}")
        return 0

    if args.cmd == "append":
        raw = args.json.strip() if args.json else sys.stdin.read()
        record = json.loads(raw)
        out = append_encounter_sequence_line(root, record)
        print(f"appended to {out}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
