#!/usr/bin/env python3
"""Validate 4-axis promotion gate policy SSOT + cascade-forbidden invariants."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_MD = ROOT / "docs/final/artifacts/mkm_multi_axis_promotion_gate_policy_v1.md"
OUT = ROOT / "docs/final/artifacts/mkm_multi_axis_promotion_gate_policy_v1_latest.json"
REPORT = ROOT / "reports/mkm_multi_axis_promotion_gate_policy_validation_v1_latest.json"

AXES = ("AX-1", "AX-2", "AX-2-PoC", "AX-3", "AX-4")
FORBIDDEN_INFERENCES = (
    "rib55 adjudication",
    "COORD wire",
    "MASK Tier A",
    "repair_v2",
    "send_gate",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-md", type=Path, default=POLICY_MD)
    args = ap.parse_args()

    if not args.policy_md.is_file():
        raise SystemExit(f"missing policy: {args.policy_md}")

    text = args.policy_md.read_text(encoding="utf-8")
    checks: list[dict] = []

    checks.append({"name": "schema_frontmatter", "ok": "schema: mkm_multi_axis_promotion_gate_policy_v1" in text})
    checks.append({"name": "promotion_cascade_forbidden", "ok": "promotion_cascade_forbidden: true" in text})
    checks.append({"name": "send_gate_hold", "ok": "send_gate: HOLD" in text or "send_gate` | **HOLD**" in text})
    checks.append({"name": "fail_comp_004", "ok": "FAIL-COMP-004" in text})
    for ax in AXES:
        checks.append({"name": f"axis_{ax}", "ok": ax in text})
    checks.append({"name": "raw_gate_mention", "ok": "alignment_pass_rate(raw)" in text})
    checks.append({"name": "rib55_not_track_a_substitute", "ok": "대체" in text and "rib55" in text})

    sku_brief = ROOT / "docs/final/artifacts/compression_sku_separation_brief_v1_latest.json"
    checks.append({"name": "sku_brief_pointer_exists", "ok": sku_brief.is_file()})

    doc = {
        "schema": "mkm_multi_axis_promotion_gate_policy_validation_v1",
        "generated_at_utc": _utc(),
        "policy_md": str(args.policy_md.relative_to(ROOT)).replace("\\", "/"),
        "axes": list(AXES),
        "promotion_cascade_forbidden": True,
        "send_gate": "HOLD",
        "research_only": True,
        "checks": checks,
        "ok": all(c["ok"] for c in checks),
        "forbidden_inference_keywords": list(FORBIDDEN_INFERENCES),
        "reproduce": "py scripts/validate_mkm_multi_axis_promotion_gate_policy_v1.py",
        "coord_poc_reproduce": "py scripts/run_rib55_coord_passive_audit_v1.py --skip-pytest",
    }

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    REPORT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(OUT)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
