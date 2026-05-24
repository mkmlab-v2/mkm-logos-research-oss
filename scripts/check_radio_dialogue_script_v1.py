#!/usr/bin/env python3
"""O-P31c Zone B gate — validate radio_dialogue_script_v1 + public copy guard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_radio_program_skin_v1 import get_skin  # noqa: E402

DEFAULT_SCHEMA = ROOT / "docs" / "final" / "schemas" / "radio_dialogue_script_v1.schema.json"
DEFAULT_SCRIPT = ROOT / "reports" / "radio_dialogue_script_morning_shorts_latest.json"
DEFAULT_OUT = ROOT / "reports" / "radio_dialogue_script_gate_latest.json"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate_jsonschema(doc: Dict[str, Any], schema_path: Path) -> List[str]:
    if not schema_path.is_file():
        return [f"missing_schema:{schema_path}"]
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        return []
    schema = _read_json(schema_path)
    errs: List[str] = []
    for e in Draft7Validator(schema).iter_errors(doc):
        errs.append(f"schema:{list(e.path)}:{e.message}")
    return errs[:30]


def _collect_audio_text(doc: Dict[str, Any]) -> List[str]:
    texts: List[str] = []
    for seg in doc.get("segments") or []:
        for d in seg.get("dialogue") or []:
            t = d.get("audio_text")
            if t:
                texts.append(str(t))
    return texts


def check_radio_dialogue_script(
    doc: Dict[str, Any],
    *,
    schema_path: Path = DEFAULT_SCHEMA,
) -> Dict[str, Any]:
    reasons: List[str] = []
    reasons.extend(_validate_jsonschema(doc, schema_path))

    if doc.get("schema") != "radio_dialogue_script_v1":
        reasons.append("schema_const_mismatch")
    if doc.get("non_gating") is not True:
        reasons.append("non_gating_required")
    gates = doc.get("gates") or {}
    if gates.get("spoken_price_allowed") is not False:
        reasons.append("spoken_price_allowed_must_be_false")
    if (gates.get("track_a_webhook_count") or 0) != 0:
        reasons.append("track_a_webhook_count_must_be_zero")

    wall = doc.get("track_wall") or {}
    for k in ("live_trading_trigger", "track_a_order_path", "clinical_diagnosis"):
        if wall.get(k) is not False:
            reasons.append(f"track_wall.{k}_must_be_false")

    skin = get_skin(doc)
    if doc.get("program_skin") and doc.get("program_skin") != skin.skin_id:
        reasons.append("program_skin_mismatch")

    texts = _collect_audio_text(doc)
    if not texts:
        reasons.append("no_dialogue_lines")
    else:
        opening = texts[0]
        if not skin.disclaimer_ok(opening):
            reasons.append("opening_disclaimer_incomplete")

    forbidden_hits: List[str] = []
    for i, t in enumerate(texts):
        if i == 0 and skin.disclaimer_ok(t):
            continue
        for hit in skin.scan_forbidden(t):
            forbidden_hits.append(f"line_{i + 1}:{hit}")
    if forbidden_hits:
        reasons.extend(forbidden_hits[:20])

    ok = len(reasons) == 0
    return {
        "schema": "radio_dialogue_script_gate_v1",
        "checked_at_utc": doc.get("generated_at_utc"),
        "briefing_id": doc.get("briefing_id"),
        "program_style": doc.get("program_style"),
        "program_skin": skin.skin_id,
        "gate_ok": ok,
        "reasons": reasons,
        "n_dialogue_lines": len(texts),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate radio_dialogue_script_v1 JSON.")
    ap.add_argument("--script-json", type=Path, default=DEFAULT_SCRIPT)
    ap.add_argument("--schema-json", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    path = args.script_json if args.script_json.is_absolute() else ROOT / args.script_json
    if not path.is_file():
        print(f"FAIL: missing script json: {path}", file=sys.stderr)
        return 2

    doc = _read_json(path)
    report = check_radio_dialogue_script(doc, schema_path=args.schema_json)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
    else:
        out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
        script_key = str(args.script_json).replace("\\", "/").lower()
        if "friday" in script_key:
            sidecar = ROOT / "reports" / "radio_dialogue_script_gate_friday_latest.json"
        elif "health" in script_key:
            sidecar = ROOT / "reports" / "radio_dialogue_script_gate_health_latest.json"
        elif "morning" in script_key or "shorts" in script_key:
            sidecar = ROOT / "reports" / "radio_dialogue_script_gate_morning_latest.json"
        else:
            sidecar = None
        if sidecar is not None:
            sidecar.write_text(payload + "\n", encoding="utf-8")
        print(payload)

    return 0 if report.get("gate_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
