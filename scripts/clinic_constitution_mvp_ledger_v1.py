"""
Append validated clinic constitution MVP capture lines (B-track, physician gold).

Separate from sasang_dynamics_regime_mapping_ledger (market/regime). Stdlib only.
Schema: docs/final/schemas/clinic_constitution_mvp_capture_v1.schema.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_DATA_REL = Path("data/clinic")
LEDGER_PREFIX = "clinic_constitution_mvp_v1"
SAMPLE_REL = WORKSPACE_DATA_REL / "clinic_constitution_mvp_v1.sample.jsonl"

CONSTITUTION_LABELS = frozenset(
    {"taeeum", "soyang", "taeyang", "soeum", "uncertain", "withheld"}
)
PROXY_KEYS = ("cold_heat_lean", "digestion_lean", "activity_lean", "moisture_lean")
DISAGREEMENT_CODES = frozenset(
    {
        "none",
        "ai_overconfident",
        "ai_underconfident",
        "modality_insufficient",
        "physician_withheld",
    }
)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _proxy_ok(v: Any, key: str, errors: list[str]) -> None:
    if not isinstance(v, (int, float)):
        errors.append(f"observation_proxies.{key} must be number")
    elif v < 0 or v > 1:
        errors.append(f"observation_proxies.{key} must be in [0, 1]")


def validate_clinic_capture_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record must be a JSON object"]

    for key in (
        "schema",
        "version",
        "ts_utc",
        "hypothesis_tier",
        "boundary_ack",
        "a_track_autobind_forbidden",
        "encounter",
        "observation_proxies",
        "ai_hypothesis",
        "physician_constitution",
    ):
        if key not in record:
            errors.append(f"missing required key: {key}")
    if errors:
        return errors

    if record.get("schema") != "clinic_constitution_mvp_capture_v1":
        errors.append("schema must be clinic_constitution_mvp_capture_v1")

    if record["hypothesis_tier"] != "B":
        errors.append("hypothesis_tier must be 'B'")
    if record["boundary_ack"] is not True:
        errors.append("boundary_ack must be true")
    if record["a_track_autobind_forbidden"] is not True:
        errors.append("a_track_autobind_forbidden must be true")

    ts = record["ts_utc"]
    if not isinstance(ts, str) or not ts.strip():
        errors.append("ts_utc must be a non-empty string")

    enc = record["encounter"]
    if not isinstance(enc, dict) or not isinstance(enc.get("ref_token"), str) or not enc[
        "ref_token"
    ].strip():
        errors.append("encounter.ref_token must be a non-empty string")

    op = record["observation_proxies"]
    if not isinstance(op, dict):
        errors.append("observation_proxies must be object")
    else:
        for k in PROXY_KEYS:
            if k not in op:
                errors.append(f"observation_proxies missing: {k}")
            else:
                _proxy_ok(op[k], k, errors)

    ai = record["ai_hypothesis"]
    if not isinstance(ai, dict):
        errors.append("ai_hypothesis must be object")
    else:
        c = ai.get("constitution")
        if c not in {"taeeum", "soyang", "taeyang", "soeum", "uncertain"}:
            errors.append("ai_hypothesis.constitution invalid")
        conf = ai.get("confidence")
        if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
            errors.append("ai_hypothesis.confidence must be in [0, 1]")

    pc = record["physician_constitution"]
    if not isinstance(pc, dict):
        errors.append("physician_constitution must be object")
    else:
        if pc.get("label") not in CONSTITUTION_LABELS:
            errors.append("physician_constitution.label invalid")
        if pc.get("recorded_by_role") != "licensed_km_physician":
            errors.append("physician_constitution.recorded_by_role must be licensed_km_physician")

    agr = record.get("agreement")
    if agr is not None:
        if not isinstance(agr, dict):
            errors.append("agreement must be object if present")
        else:
            dc = agr.get("disagreement_code")
            if dc is not None and dc not in DISAGREEMENT_CODES:
                errors.append("agreement.disagreement_code invalid")

    return errors


def append_clinic_capture_line(
    workspace_root: Path,
    record: dict[str, Any],
    *,
    set_ts_if_missing: bool = True,
) -> Path:
    errs = validate_clinic_capture_record(record)
    if errs:
        raise ValueError("; ".join(errs))
    out_dir = workspace_root / WORKSPACE_DATA_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    daily = out_dir / f"{LEDGER_PREFIX}_{now.strftime('%Y%m%d')}.jsonl"
    payload = dict(record)
    if set_ts_if_missing and not str(payload.get("ts_utc", "")).strip():
        payload["ts_utc"] = now.isoformat().replace("+00:00", "Z")
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
        errs = validate_clinic_capture_record(obj)
        if errs:
            raise ValueError(f"line {i}: {'; '.join(errs)}")
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Clinic constitution MVP capture JSONL append/validate (B-track)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate-sample", help="Validate bundled sample JSONL")
    p_val.add_argument("--path", type=Path, default=None)

    p_app = sub.add_parser("append", help="Append one JSON object from stdin or --json")
    p_app.add_argument("--json", type=str, default="")

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
        out = append_clinic_capture_line(root, record)
        print(f"appended to {out}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
