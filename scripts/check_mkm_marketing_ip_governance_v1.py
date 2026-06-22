#!/usr/bin/env python3
"""P0 marketing/IP governance gate — thin wrapper over showroom positioning Fact-Lock."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from check_logos_showroom_positioning_fact_lock_v1 import (
    DEFAULT_SSOT,
    ROOT,
    _rel,
    _utc,
    check as check_positioning,
)

DEFAULT_CHARTER = ROOT / "docs/final/artifacts/mkm_marketing_ip_governance_charter_draft_v1.json"
DEFAULT_OUT = ROOT / "reports/mkm_marketing_ip_governance_gate_v1_latest.json"

# P0 public static surfaces beyond positioning SCAN_PATHS (deploy / showroom bundle).
P0_PUBLIC_EXTRA_SCAN_PATHS = [
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/logos_cosmic_meta_architecture_ui_v1.json",
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/.showroom_staging/logos_cosmic_meta_architecture_ui_v1.json",
    ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_meta_architecture_ui_v1.json",
]


def _load_blocklist(charter_path: Path) -> list[str]:
    if not charter_path.is_file():
        return []
    charter = json.loads(charter_path.read_text(encoding="utf-8-sig"))
    return list(charter.get("internal_term_blocklist_public") or [])


def _scan_internal_terms(paths: list[Path], blocklist: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for path in paths:
        rel = _rel(path)
        if not path.is_file():
            failures.append(f"missing p0 scan file: {rel}")
            rows.append({"path": rel, "missing": True, "internal_term_hits": []})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = sorted({term for term in blocklist if term and term in text})
        rows.append({"path": rel, "missing": False, "internal_term_hits": hits})
        if hits:
            failures.append(f"{path.name}: L3 internal term leak {hits}")
    return rows, failures


def check(*, ssot_path: Path, charter_path: Path) -> dict[str, Any]:
    from check_logos_showroom_positioning_fact_lock_v1 import SCAN_PATHS

    blocklist = _load_blocklist(charter_path)
    pos = check_positioning(ssot_path=ssot_path, scan_paths=SCAN_PATHS)
    p0_rows, p0_failures = _scan_internal_terms(P0_PUBLIC_EXTRA_SCAN_PATHS, blocklist)

    gate_failures = list(pos.get("gate_failures") or []) + p0_failures
    ok = len(gate_failures) == 0

    return {
        "schema": "mkm_marketing_ip_governance_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ok": ok,
        "gate_pass": ok,
        "gate_failures": gate_failures,
        "charter_path": _rel(charter_path),
        "blocklist_count": len(blocklist),
        "positioning_gate": {
            "ok": pos.get("ok"),
            "gate_failures": pos.get("gate_failures"),
            "out_path": "reports/logos_showroom_positioning_fact_lock_gate_v1_latest.json",
        },
        "p0_internal_term_scan": p0_rows,
        "reproducible_command": "py scripts/check_mkm_marketing_ip_governance_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssot", type=Path, default=DEFAULT_SSOT)
    ap.add_argument("--charter", type=Path, default=DEFAULT_CHARTER)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.ssot.is_file():
        print(f"missing ssot: {args.ssot}", file=sys.stderr)
        return 2

    doc = check(ssot_path=args.ssot, charter_path=args.charter)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Keep positioning gate artifact in sync for downstream tooling.
    from check_logos_showroom_positioning_fact_lock_v1 import SCAN_PATHS, check as check_positioning

    pos_doc = check_positioning(ssot_path=args.ssot, scan_paths=SCAN_PATHS)
    pos_out = ROOT / "reports/logos_showroom_positioning_fact_lock_gate_v1_latest.json"
    pos_out.write_text(json.dumps(pos_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {"ok": doc["ok"], "gate_failures": doc["gate_failures"], "out": str(args.output)},
            ensure_ascii=False,
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
