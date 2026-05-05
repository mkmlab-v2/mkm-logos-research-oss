#!/usr/bin/env python3
"""Validate btc_frame_governance_stage_payload_v1 JSON.

Exit codes:
  0 OK
  1 schema/JSON validation failed
  2 required field contract mismatch
  3 live eligibility requirements not met
  4 referenced approval path missing/mismatch
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "final" / "artifacts" / "schemas" / "btc_frame_governance_stage_payload_v1.schema.json"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_schema(doc: Dict[str, Any]) -> tuple[bool, str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:
        return False, f"jsonschema required: {e}"
    schema = _load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errs = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if errs:
        msg = "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:16])
        return False, msg
    return True, ""


def _resolve_path(workspace: Path, value: Optional[str]) -> Optional[Path]:
    if not value:
        return None
    p = Path(value)
    return p if p.is_absolute() else (workspace / p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", type=Path, required=True, help="btc_frame_governance_stage_payload_v1 JSON path")
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--risk-json", type=Path, default=None, help="Optional gate risk JSON path to cross-check gate_input.risk_profile_ref")
    ap.add_argument(
        "--approval-json",
        type=Path,
        default=None,
        help="Optional approval path to match against risk_gate.human_approval_ref",
    )
    ap.add_argument(
        "--require-live-eligible",
        action="store_true",
        help="Require payload to be live-trade eligible (A/gate/go/live_allowed/etc).",
    )
    args = ap.parse_args()

    workspace = args.workspace_root.resolve()
    payload_path = args.payload.resolve()
    if not SCHEMA_PATH.is_file():
        print(f"MISSING_SCHEMA: {SCHEMA_PATH}", file=sys.stderr)
        return 1
    try:
        payload = _load_json(payload_path)
    except OSError as e:
        print(f"READ_ERROR: {payload_path}: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"JSON_ERROR: {e}", file=sys.stderr)
        return 1

    ok, msg = _validate_schema(payload)
    if not ok:
        print(f"SCHEMA_ERROR: {msg}", file=sys.stderr)
        return 1

    stage = str(payload.get("stage") or "")
    if stage == "gate" and args.risk_json is not None:
        gate_input = ((payload.get("inputs") or {}).get("gate_input") or {})
        ref = str(gate_input.get("risk_profile_ref") or "")
        expected = args.risk_json.resolve()
        got = _resolve_path(workspace, ref)
        if got is None or got.resolve() != expected:
            print(
                f"RISK_REF_MISMATCH: payload risk_profile_ref={ref!r} expected={str(expected)!r}",
                file=sys.stderr,
            )
            return 2

    if args.require_live_eligible:
        outputs = payload.get("outputs") or {}
        risk_gate = payload.get("risk_gate") or {}
        action = str(outputs.get("action") or "")
        track = str(payload.get("track") or "")
        stage = str(payload.get("stage") or "")
        conf = outputs.get("confidence_score")
        min_conf = risk_gate.get("min_conf_threshold", 0.8)
        if not isinstance(conf, (int, float)) or not isinstance(min_conf, (int, float)):
            print("LIVE_NOT_ELIGIBLE: confidence_score/min_conf_threshold missing or invalid.", file=sys.stderr)
            return 3
        if not (
            track == "A"
            and stage == "gate"
            and action == "go"
            and bool(risk_gate.get("live_allowed")) is True
            and bool(risk_gate.get("regime_gate_passed")) is True
            and bool(risk_gate.get("human_approval_required")) is True
            and float(conf) >= float(min_conf)
        ):
            print("LIVE_NOT_ELIGIBLE: payload does not satisfy live eligibility contract.", file=sys.stderr)
            return 3
        href = str(risk_gate.get("human_approval_ref") or "")
        if not href:
            print("LIVE_NOT_ELIGIBLE: human_approval_ref required for live eligibility.", file=sys.stderr)
            return 4

    if args.approval_json is not None:
        risk_gate = payload.get("risk_gate") or {}
        href = str(risk_gate.get("human_approval_ref") or "")
        resolved_href = _resolve_path(workspace, href)
        resolved_arg = args.approval_json.resolve()
        if resolved_href is None or resolved_href.resolve() != resolved_arg:
            print(
                f"APPROVAL_REF_MISMATCH: payload human_approval_ref={href!r} expected={str(resolved_arg)!r}",
                file=sys.stderr,
            )
            return 4
        if not resolved_arg.is_file():
            print(f"MISSING_APPROVAL_FILE: {resolved_arg}", file=sys.stderr)
            return 4

    print("OK: btc_frame_governance_stage_payload_v1 validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

