"""
Append validated B-track Sasang dynamics → regime hypothesis lines to data/sasang/.

Separate from live trading and dual_regime_api; mirrors MYEONGNI B-track ledger pattern.
Validation aligns with docs/final/SASANG_DYNAMICS_REGIME_MAPPING_JSON_SCHEMA.json (stdlib only).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_DATA_REL = Path("data/sasang")
LEDGER_PREFIX = "sasang_dynamics_regime_mapping"
SAMPLE_REL = WORKSPACE_DATA_REL / "sasang_dynamics_regime_mapping_v1.sample.jsonl"
MAPPING_TARGETS = frozenset({"bull", "bear", "sideways"})
REGIME_HYP = frozenset(
    {"expansion", "contraction", "phase_transition", "extreme_tail", "neutral"}
)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_sasang_record(record: dict[str, Any]) -> list[str]:
    """Return list of error strings; empty means valid."""
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    for key in (
        "ts_utc",
        "hypothesis_tier",
        "boundary_ack",
        "stub",
        "a_track_autobind_forbidden",
        "machine_readables",
    ):
        if key not in record:
            errors.append(f"missing required key: {key}")
    if errors:
        return errors

    ts = record["ts_utc"]
    if not isinstance(ts, str) or not ts.strip():
        errors.append("ts_utc must be a non-empty string")

    if record["hypothesis_tier"] != "B":
        errors.append("hypothesis_tier must be 'B'")

    if record["boundary_ack"] is not True:
        errors.append("boundary_ack must be true")

    stub = record["stub"]
    if not isinstance(stub, (str, bool)):
        errors.append("stub must be string or boolean")

    if record["a_track_autobind_forbidden"] is not True:
        errors.append("a_track_autobind_forbidden must be true")

    mr = record["machine_readables"]
    if not isinstance(mr, dict):
        errors.append("machine_readables must be object")
    else:
        for k in ("heat_proxy", "cold_proxy", "volatility_rarefaction_proxy"):
            if k not in mr:
                errors.append(f"machine_readables missing: {k}")
            else:
                v = mr[k]
                if not isinstance(v, (int, float)):
                    errors.append(f"machine_readables.{k} must be number")
                elif v < 0 or v > 1:
                    errors.append(f"machine_readables.{k} must be in [0, 1]")

    ver = record.get("sasang_lens_version")
    if ver is not None:
        if not isinstance(ver, str) or not ver.strip():
            errors.append("sasang_lens_version must be non-empty string if present")

    rh = record.get("regime_hypothesis")
    if rh is not None:
        if rh not in REGIME_HYP:
            errors.append(
                "regime_hypothesis must be one of expansion|contraction|phase_transition|extreme_tail|neutral if present"
            )

    mt = record.get("mapping_target")
    if mt is not None:
        if not isinstance(mt, str) or mt not in MAPPING_TARGETS:
            errors.append("mapping_target must be one of bull|bear|sideways if present")

    hr = record.get("human_readable")
    if hr is not None and not isinstance(hr, dict):
        errors.append("human_readable must be object if present")

    return errors


def append_sasang_dynamics_line(
    workspace_root: Path,
    record: dict[str, Any],
    *,
    set_ts_if_missing: bool = True,
) -> Path:
    errs = validate_sasang_record(record)
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
        errs = validate_sasang_record(obj)
        if errs:
            raise ValueError(f"line {i}: {'; '.join(errs)}")
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="B-track Sasang dynamics regime mapping JSONL append/validate"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate-sample", help="Validate bundled sample JSONL")
    p_val.add_argument(
        "--path",
        type=Path,
        default=None,
        help="JSONL path (default: data/sasang/...sample.jsonl)",
    )

    p_app = sub.add_parser("append", help="Append one JSON object from stdin or --json")
    p_app.add_argument(
        "--json",
        type=str,
        default="",
        help="JSON object string (if empty, read stdin)",
    )

    args = p.parse_args(argv)
    root = _workspace_root()

    if args.cmd == "validate-sample":
        path = args.path or (root / SAMPLE_REL)
        n = validate_jsonl_file(path)
        print(f"OK: {n} line(s) validated: {path}")
        return 0

    if args.cmd == "append":
        raw = args.json.strip() if args.json else sys.stdin.read()
        record = json.loads(raw)
        out = append_sasang_dynamics_line(root, record)
        print(f"appended to {out}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
