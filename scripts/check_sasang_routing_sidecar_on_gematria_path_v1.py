#!/usr/bin/env python3
"""Gate: sasang routing sidecar on gematria path — schema + forbidden-edge walls."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs/final/artifacts/sasang_routing_sidecar_on_gematria_path_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sasang_routing_sidecar_on_gematria_path_gate_v1_latest.json"

FORBIDDEN_KEYS = (
    "merged_score",
    "gematria_sasang_product",
    "prophecy_vote_weight",
    "constitutional_quadrant",
    "constitutional_diagnosis",
    "track_a_promotion",
    "compression_floor_override",
)

REQUIRED_MUST_NOT = {
    "prophecy_vote",
    "track_a_compression_floor",
    "production_gematria_kernel",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _walk_keys(obj: Any, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            keys.append(path)
            keys.extend(_walk_keys(v, path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            keys.extend(_walk_keys(v, f"{prefix}[{i}]"))
    return keys


def evaluate(doc: dict[str, Any]) -> tuple[bool, list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    if doc.get("schema") != "sasang_routing_sidecar_on_gematria_path_v1":
        errors.append("schema mismatch")
    checks.append({"kind": "schema", "ok": doc.get("schema") == "sasang_routing_sidecar_on_gematria_path_v1"})

    for flag, expected in (
        ("research_only", True),
        ("non_gating", True),
        ("track_a_blocked", True),
        ("forbidden_synthesis_ack", True),
    ):
        ok = doc.get(flag) is expected
        checks.append({"kind": flag, "ok": ok})
        if not ok:
            errors.append(f"{flag} must be {expected}")

    if str(doc.get("send_gate", "")).upper() != "HOLD":
        errors.append("send_gate must be HOLD")

    all_keys = _walk_keys(doc)
    for bad in FORBIDDEN_KEYS:
        hits = [k for k in all_keys if re.search(rf"(^|\.){re.escape(bad)}$", k)]
        ok = not hits
        checks.append({"kind": f"forbidden_key:{bad}", "ok": ok, "hits": hits[:5]})
        if hits:
            errors.append(f"forbidden key present: {bad}")

    must_not = set(doc.get("must_not_merge_into") or [])
    missing = REQUIRED_MUST_NOT - must_not
    checks.append({"kind": "must_not_merge_into", "ok": not missing, "missing": sorted(missing)})
    if missing:
        errors.append(f"must_not_merge_into missing: {sorted(missing)}")

    hints = doc.get("sasang_routing_hints") or {}
    flags = set(hints.get("forbidden_flags") or [])
    for required in ("no_prophecy_vote_merge", "no_score_linear_blend"):
        ok = required in flags
        checks.append({"kind": f"forbidden_flag:{required}", "ok": ok})
        if not ok:
            errors.append(f"forbidden_flags missing {required}")

    gem = doc.get("gematria_path_ref") or {}
    recipe = str(gem.get("recipe_id") or "")
    if recipe not in ("gematria_to_4d_bridge", "gematria_to_4d_bridge_sandbox_v1"):
        errors.append(f"invalid gematria recipe_id: {recipe!r}")

    return (not errors), errors, checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.inp.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {args.inp}"}))
        return 1

    doc = _load(args.inp)
    ok, errors, checks = evaluate(doc)
    report = {
        "schema": "sasang_routing_sidecar_on_gematria_path_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "ok": ok,
        "decision": "PASS" if ok else "FAIL",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "input": str(args.inp.relative_to(ROOT)).replace("\\", "/"),
        "errors": errors,
        "checks": checks,
        "reproduce": "py scripts/check_sasang_routing_sidecar_on_gematria_path_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "decision": report["decision"], "errors": len(errors)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
