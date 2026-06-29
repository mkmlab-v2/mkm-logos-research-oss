#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-LLM / post-build gate — validate four_slot payload + optional envelope policy."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"
DEFAULT_ENVELOPE = ROOT / "docs/final/artifacts/logos_four_slot_generation_envelope_v1_latest.json"
OUT = ROOT / "reports/magic_orb_four_slot_post_llm_gate_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _envelope_policy_ok(envelope: dict[str, Any], insight: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not envelope:
        return errors
    policy = envelope.get("policy") or {}
    if policy.get("send_gate") and policy.get("send_gate") != "HOLD":
        errors.append("envelope policy send_gate must be HOLD")
    four = insight.get("four_slot_response_v1") or {}
    enf = four.get("enforcement") or {}
    if four and enf.get("send_gate") != "HOLD":
        errors.append("insight four_slot send_gate must be HOLD")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Post-LLM four-slot gate for magic orb insight.")
    ap.add_argument("--insight-json", type=Path, default=DEFAULT_INSIGHT)
    ap.add_argument("--envelope-json", type=Path, default=DEFAULT_ENVELOPE)
    ap.add_argument("--allow-missing-four-slot", action="store_true")
    ap.add_argument("--skip-envelope", action="store_true")
    args = ap.parse_args()

    insight_path = args.insight_json if args.insight_json.is_absolute() else ROOT / args.insight_json
    if not insight_path.is_file():
        print(json.dumps({"ok": False, "error": "missing_insight"}, ensure_ascii=False))
        return 1

    validate_cmd = [
        PY,
        str(ROOT / "scripts/validate_magic_orb_four_slot_v1.py"),
        "--insight-json",
        str(insight_path),
    ]
    if args.allow_missing_four_slot:
        validate_cmd.append("--allow-missing-four-slot")

    proc = subprocess.run(validate_cmd, cwd=str(ROOT), capture_output=True, text=True)
    validate_out: dict[str, Any] = {}
    try:
        validate_out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        validate_out = {"ok": False, "raw": proc.stdout, "stderr": proc.stderr}

    insight = _load(insight_path)
    envelope_errors: list[str] = []
    if not args.skip_envelope:
        env_path = args.envelope_json if args.envelope_json.is_absolute() else ROOT / args.envelope_json
        envelope = _load(env_path) if env_path.is_file() else {}
        envelope_errors = _envelope_policy_ok(envelope, insight)

    ok = proc.returncode == 0 and not envelope_errors
    doc = {
        "schema": "magic_orb_four_slot_post_llm_gate_v1",
        "ok": ok,
        "validate": validate_out,
        "envelope_errors": envelope_errors,
        "insight_path": str(insight_path),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
