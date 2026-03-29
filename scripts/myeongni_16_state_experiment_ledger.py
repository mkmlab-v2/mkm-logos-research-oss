"""
Append validated B-track 16-state experiment lines to workspace data/myeongni/.

Not production fusion ledger; separate from projects/bitcoin-trading memory/v2/ledger.
Validation mirrors docs/final/MYEONGNI_16_STATE_EXPERIMENT_JSON_SCHEMA.json (stdlib only).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_DATA_REL = Path("data/myeongni")
LEDGER_PREFIX = "myeongni_16_state_experiment"
SAMPLE_REL = WORKSPACE_DATA_REL / "myeongni_16_state_experiment_v1.sample.jsonl"
MAPPING_TARGETS = frozenset({"bull", "bear", "sideways"})


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_experiment_record(record: dict[str, Any]) -> list[str]:
    """Return list of error strings; empty means valid."""
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    for key in ("ts_utc", "hypothesis_tier", "boundary_ack", "stub"):
        if key not in record:
            errors.append(f"missing required key: {key}")
    if errors:
        return errors
    ts = record["ts_utc"]
    if not isinstance(ts, str) or not ts.strip():
        errors.append("ts_utc must be a non-empty string")
    ht = record["hypothesis_tier"]
    if ht != "B":
        errors.append("hypothesis_tier must be 'B'")
    if record["boundary_ack"] is not True:
        errors.append("boundary_ack must be true")
    stub = record["stub"]
    if not isinstance(stub, (str, bool)):
        errors.append("stub must be string or boolean (per schema oneOf)")
    sid = record.get("state_id")
    if sid is not None:
        if not isinstance(sid, int) or sid < 1 or sid > 16:
            errors.append("state_id must be integer 1..16 if present")
    mt = record.get("mapping_target")
    if mt is not None:
        if not isinstance(mt, str) or mt not in MAPPING_TARGETS:
            errors.append("mapping_target must be one of bull|bear|sideways if present")
    v4 = record.get("vector_4d")
    if v4 is not None:
        if not isinstance(v4, dict):
            errors.append("vector_4d must be object if present")
        else:
            for k, v in v4.items():
                if not isinstance(v, (int, float)):
                    errors.append(f"vector_4d.{k} must be number")
    for rate_key in ("consistency_rate", "self_contradiction_rate"):
        rv = record.get(rate_key)
        if rv is not None:
            if not isinstance(rv, (int, float)):
                errors.append(f"{rate_key} must be number if present")
            elif rv < 0 or rv > 1:
                errors.append(f"{rate_key} must be in [0, 1] if present")
    return errors


def append_myeongni_16_state_experiment(
    workspace_root: Path,
    record: dict[str, Any],
    *,
    set_ts_if_missing: bool = True,
) -> Path:
    errs = validate_experiment_record(record)
    if errs:
        raise ValueError("; ".join(errs))
    out_dir = workspace_root / WORKSPACE_DATA_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    daily = out_dir / f"{LEDGER_PREFIX}_{now.strftime('%Y%m%d')}.jsonl"
    payload = dict(record)
    if set_ts_if_missing and not payload.get("ts_utc"):
        payload["ts_utc"] = now.isoformat()
    with daily.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return daily


def validate_jsonl_file(path: Path) -> int:
    """Return number of lines; raises ValueError on first bad line."""
    text = path.read_text(encoding="utf-8")
    n = 0
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        errs = validate_experiment_record(obj)
        if errs:
            raise ValueError(f"line {i}: {'; '.join(errs)}")
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="B-track 16-state experiment JSONL append/validate")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate-sample", help="Validate bundled sample JSONL")
    p_val.add_argument(
        "--path",
        type=Path,
        default=None,
        help="JSONL path (default: data/myeongni/myeongni_16_state_experiment_v1.sample.jsonl)",
    )

    p_app = sub.add_parser("append", help="Append one record from --json string")
    p_app.add_argument("--json", required=True, help="JSON object string")

    args = p.parse_args(argv)
    root = _workspace_root()

    if args.cmd == "validate-sample":
        sample = args.path or (root / SAMPLE_REL)
        if not sample.is_file():
            print(f"not found: {sample}", file=sys.stderr)
            return 2
        try:
            n = validate_jsonl_file(sample)
        except (json.JSONDecodeError, ValueError) as e:
            print(str(e), file=sys.stderr)
            return 1
        print(f"ok: {n} line(s) validated: {sample}")
        return 0

    if args.cmd == "append":
        try:
            obj = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(str(e), file=sys.stderr)
            return 1
        if not isinstance(obj, dict):
            print("JSON must be an object", file=sys.stderr)
            return 1
        try:
            out = append_myeongni_16_state_experiment(root, obj)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        print(str(out))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
