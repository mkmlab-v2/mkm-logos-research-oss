#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "artifacts" / "schemas" / "mkm_myeongni_response_v2.schema.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _num_between(v: Any, lo: float, hi: float) -> bool:
    return isinstance(v, (int, float)) and lo <= float(v) <= hi


def validate(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if doc.get("schema") != "mkm_myeongni_response_v2":
        errs.append("schema must be mkm_myeongni_response_v2")

    track = str(doc.get("track") or "")
    if track not in {"A", "B"}:
        errs.append("track must be A or B")

    core = doc.get("core_layer") if isinstance(doc.get("core_layer"), dict) else None
    if core is None:
        errs.append("core_layer missing")
    else:
        if not _num_between(core.get("direction_core"), -1.0, 1.0):
            errs.append("core_layer.direction_core must be in [-1,1]")
        if not _num_between(core.get("confidence_core"), 0.0, 1.0):
            errs.append("core_layer.confidence_core must be in [0,1]")
        if not isinstance(core.get("ten_god_balance"), (int, float)):
            errs.append("core_layer.ten_god_balance must be numeric")
        if not isinstance(core.get("jijangan_pressure"), (int, float)):
            errs.append("core_layer.jijangan_pressure must be numeric")

    coord = doc.get("coordinator_layer") if isinstance(doc.get("coordinator_layer"), dict) else None
    if coord is None:
        errs.append("coordinator_layer missing")
    else:
        if not isinstance(coord.get("direction_override_allowed"), bool):
            errs.append("coordinator_layer.direction_override_allowed must be boolean")
        if not _num_between(coord.get("weather_calibration_term"), -0.2, 0.2):
            errs.append("coordinator_layer.weather_calibration_term must be in [-0.2,0.2]")
        if not _num_between(coord.get("confidence_adjusted"), 0.0, 1.0):
            errs.append("coordinator_layer.confidence_adjusted must be in [0,1]")
        fck = coord.get("failed_check_keys")
        if not isinstance(fck, list) or any(not isinstance(x, str) for x in fck):
            errs.append("coordinator_layer.failed_check_keys must be string array")

    final_action = doc.get("final_action") if isinstance(doc.get("final_action"), dict) else None
    if final_action is None:
        errs.append("final_action missing")
    else:
        if str(final_action.get("decision") or "") not in {"HOLD", "WATCH", "REDUCE"}:
            errs.append("final_action.decision must be HOLD/WATCH/REDUCE")

    gov = doc.get("governance") if isinstance(doc.get("governance"), dict) else None
    if gov is None:
        errs.append("governance missing")
    else:
        if not isinstance(gov.get("research_only"), bool):
            errs.append("governance.research_only must be boolean")
        if not isinstance(gov.get("human_signoff_required"), bool):
            errs.append("governance.human_signoff_required must be boolean")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate MKM Myeongni response v2 contract.")
    ap.add_argument("--response-json", type=Path, required=True)
    ap.add_argument("--schema-json", type=Path, default=DEFAULT_SCHEMA)
    args = ap.parse_args()

    if not args.schema_json.is_file():
        raise SystemExit(f"missing schema file: {args.schema_json}")
    # lightweight presence check (actual checks are code-driven for portability)
    _ = _read_json(args.schema_json)
    response_path = args.response_json if args.response_json.is_absolute() else ROOT / args.response_json
    doc = _read_json(response_path)
    errs = validate(doc)
    if errs:
        print(json.dumps({"ok": False, "errors": errs}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "track": doc.get("track"), "decision": (doc.get("final_action") or {}).get("decision")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
