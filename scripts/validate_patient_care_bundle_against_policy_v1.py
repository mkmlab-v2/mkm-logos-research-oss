#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate `patient_care_bundle_v1` against `patient_care_bundle_generation_policy_v1`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "patient_care_bundle_generation_policy_v1.default.json"


def _collect_texts(bundle: dict[str, Any]) -> str:
    parts: list[str] = []
    soap = bundle.get("clinical_soap_v1") or {}
    for k in ("subjective", "objective", "assessment", "plan"):
        b = soap.get(k) or {}
        if isinstance(b.get("text"), str):
            parts.append(b["text"])
    for slot in bundle.get("patient_slots") or []:
        if isinstance(slot.get("title"), str):
            parts.append(slot["title"])
        if isinstance(slot.get("body_markdown"), str):
            parts.append(slot["body_markdown"])
        for ak in ("hypo_ack", "non_gating_ack"):
            if isinstance(slot.get(ak), str):
                parts.append(slot[ak])
    for d in bundle.get("disclaimers") or []:
        if isinstance(d, str):
            parts.append(d)
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate patient bundle against generation policy")
    ap.add_argument("--bundle-json", type=Path, required=True)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    args = ap.parse_args()

    bundle = json.loads(args.bundle_json.read_text(encoding="utf-8-sig"))
    policy = json.loads(args.policy_json.read_text(encoding="utf-8-sig"))
    hay = _collect_texts(bundle)

    for sub in policy.get("forbidden_substrings_global") or []:
        if sub and sub in hay:
            print(f"FAIL: forbidden substring matched: {sub!r}", file=sys.stderr)
            return 1

    rules = policy.get("slot_rules") or {}
    for slot in bundle.get("patient_slots") or []:
        sid = slot.get("slot_id")
        if not isinstance(sid, str):
            continue
        rule = rules.get(sid) or {}
        body = slot.get("body_markdown") or ""
        mx = rule.get("max_body_markdown_chars")
        if isinstance(mx, int) and len(body) > mx:
            print(f"FAIL: slot {sid} body exceeds max chars {mx}", file=sys.stderr)
            return 1
        for req in rule.get("required_substrings") or []:
            if req and req not in body:
                print(f"FAIL: slot {sid} missing required {req!r}", file=sys.stderr)
                return 1
        if slot.get("included") and rule.get("required_substrings_if_included"):
            for req in rule["required_substrings_if_included"]:
                if req and req not in body:
                    print(f"FAIL: slot {sid} (included) missing {req!r}", file=sys.stderr)
                    return 1

    print("OK: policy checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
