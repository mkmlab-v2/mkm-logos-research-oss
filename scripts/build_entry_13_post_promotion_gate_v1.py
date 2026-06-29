#!/usr/bin/env python3
"""Post-promotion integrity gate for ENTRY_13 shadow rail [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
PROMO = ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"
REGISTRY = ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json"
REPORT = ROOT / "reports/entry_13_post_promotion_commander_report_v1_latest.json"
P5 = ROOT / "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/entry_13_post_promotion_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _canon_clean() -> bool:
    if not CANON.is_file():
        return False
    for line in CANON.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        vid = str(row.get("verse_id") or "")
        if vid.startswith("dss:"):
            return False
    return True


def build() -> dict[str, Any]:
    promo = _load(PROMO)
    reg = _load(REGISTRY)
    report = _load(REPORT)
    p5 = _load(P5)
    sm = reg.get("summary") or {}
    checks = {
        "promotion_ok": {"passed": promo.get("promotion_ok") is True},
        "commander_verified_row": {"passed": int(sm.get("commander_verified_rows") or 0) >= 1},
        "auto_scan_honest_zero": {
            "passed": int((promo.get("checks") or {}).get("scan_complete", {}).get("auto_verified_total") or 0) == 0,
        },
        "canon_31k_clean": {"passed": _canon_clean()},
        "p5_manuscript_integrity": {"passed": p5.get("gate_ok") is True},
        "report_present": {"passed": report.get("schema") == "entry_13_post_promotion_commander_report_v1"},
        "send_gate_hold": {"passed": report.get("send_gate") == "HOLD"},
        "track_wall": {
            "passed": report.get("cross_ref_draft_mutated") is False and report.get("canon_31k_clean") is True,
        },
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "entry_13_post_promotion_gate_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "gate_ok": gate_ok,
        "checks": checks,
        "reproduce": "py scripts/build_entry_13_post_promotion_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate_ok": doc["gate_ok"]}, ensure_ascii=False))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
