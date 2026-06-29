#!/usr/bin/env python3
"""Gate: sasang routing sidecar narrative A/B — walls + panel pass floor."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports/sasang_routing_sidecar_narrative_path_ab_v1_latest.json"
OUT = ROOT / "reports/sasang_routing_sidecar_narrative_path_ab_gate_v1_latest.json"

FORBIDDEN_KEYS = ("merged_score", "gematria_sasang_product", "prophecy_vote_weight")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def evaluate(doc: dict[str, Any], *, min_sidecar_pass_rate: float) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if doc.get("schema") != "sasang_routing_sidecar_narrative_path_ab_v1":
        errors.append("schema mismatch")
    if doc.get("forbidden_synthesis_ack") is not True:
        errors.append("forbidden_synthesis_ack must be true")
    if str(doc.get("send_gate", "")).upper() != "HOLD":
        errors.append("send_gate must be HOLD")

    blob = json.dumps(doc, ensure_ascii=False)
    for key in FORBIDDEN_KEYS:
        if key in blob:
            errors.append(f"forbidden key in report: {key}")

    must_not = set(doc.get("must_not_merge_into") or [])
    for req in ("prophecy_vote", "production_gematria_kernel"):
        if req not in must_not:
            errors.append(f"must_not_merge_into missing {req}")

    on_rate = float((doc.get("arm_on") or {}).get("sidecar_gate_pass_rate") or 0)
    if on_rate < min_sidecar_pass_rate:
        errors.append(
            f"sidecar_gate_pass_rate {on_rate} < floor {min_sidecar_pass_rate}"
        )

    # Sidecar should narrow router path budget (<= 0 delta mean)
    delta_paths = float((doc.get("delta") or {}).get("narrowed_router_paths_minus_baseline") or 0)
    if delta_paths > 0:
        errors.append(f"expected narrowed router paths <= baseline; delta={delta_paths}")

    return (not errors), errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--min-sidecar-pass-rate", type=float, default=0.875)
    args = ap.parse_args()

    if not args.inp.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {args.inp}"}))
        return 1

    doc = json.loads(args.inp.read_text(encoding="utf-8-sig"))
    ok, errors = evaluate(doc, min_sidecar_pass_rate=args.min_sidecar_pass_rate)
    report = {
        "schema": "sasang_routing_sidecar_narrative_path_ab_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "ok": ok,
        "decision": "PASS" if ok else "FAIL",
        "errors": errors,
        "reproduce": "py scripts/check_sasang_routing_sidecar_narrative_path_ab_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "decision": report["decision"], "errors": len(errors)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
