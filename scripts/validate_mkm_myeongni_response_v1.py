#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "docs" / "final" / "artifacts" / "mkm_myeongni_spec_v1.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _get_path(d: dict[str, Any], dotted: str) -> Any:
    cur: Any = d
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _flatten_text(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, (int, float, bool)):
        return str(node)
    if isinstance(node, list):
        return " ".join(_flatten_text(x) for x in node)
    if isinstance(node, dict):
        return " ".join(_flatten_text(v) for v in node.values())
    return str(node)


def validate_response(doc: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    track = str(doc.get("track") or "").upper()
    if track not in {"A", "B"}:
        errs.append("track must be A or B")
        return errs

    labels = doc.get("labels")
    if not isinstance(labels, list):
        errs.append("labels must be an array")
        labels = []
    labels_set = {str(x) for x in labels}

    oc = (spec.get("output_contract") or {}).get("track_a" if track == "A" else "track_b") or {}
    required_labels = oc.get("required_labels") or []
    for lb in required_labels:
        if lb not in labels_set:
            errs.append(f"missing required label: {lb}")

    for field in oc.get("required_fields") or []:
        if _get_path(doc, field) is None:
            errs.append(f"missing required field: {field}")

    text_blob = _flatten_text(doc).lower()
    forbidden_global = [str(x).lower() for x in ((spec.get("forbidden_claims") or {}).get("global") or [])]
    for phrase in forbidden_global:
        if phrase and phrase in text_blob:
            errs.append(f"forbidden global claim found: {phrase}")

    if track == "A":
        sd = _get_path(doc, "final_action.size_guidance")
        if isinstance(sd, dict):
            mul = sd.get("size_multiplier_commander")
            if not isinstance(mul, (int, float)):
                errs.append("size_multiplier_commander must be numeric")
            else:
                lo = float(((oc.get("size_multiplier_range") or {}).get("min")) or 0.1)
                hi = float(((oc.get("size_multiplier_range") or {}).get("max")) or 1.0)
                if not (lo <= float(mul) <= hi):
                    errs.append(f"size_multiplier_commander out of range [{lo}, {hi}]: {mul}")
            if sd.get("size_policy") != "size_only":
                errs.append("size_policy must be size_only")
            if sd.get("direction_override_allowed") is not False:
                errs.append("direction_override_allowed must be false")
    else:
        decision = _get_path(doc, "final_action.decision")
        must = str(oc.get("decision_must_be") or "WATCH")
        if decision != must:
            errs.append(f"Track B decision must be {must}, got {decision}")
        # Track B: only inspect user-facing narrative fields, not guard keys.
        narrative_blob = " ".join(
            [
                _flatten_text(_get_path(doc, "final_action.medical_boundary_note")),
                _flatten_text(_get_path(doc, "observation")),
                _flatten_text(_get_path(doc, "daily_rhythm_tip")),
                _flatten_text(_get_path(doc, "stress_guard_tip")),
            ]
        ).lower()
        forbidden_med = [str(x).lower() for x in ((spec.get("forbidden_claims") or {}).get("medical") or [])]
        for phrase in forbidden_med:
            if phrase and phrase in narrative_blob:
                errs.append(f"forbidden medical claim found in narrative: {phrase}")

    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate MKM Myeongni service response against v1 spec.")
    ap.add_argument("--response-json", type=Path, required=True)
    ap.add_argument("--spec-json", type=Path, default=DEFAULT_SPEC)
    args = ap.parse_args()

    response = _read_json(args.response_json)
    spec = _read_json(args.spec_json)
    errs = validate_response(response, spec)
    if errs:
        print(json.dumps({"ok": False, "errors": errs}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "track": response.get("track"), "intent": response.get("intent")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
