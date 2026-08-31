#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Checker — governance git staging must respect blind-freeze phases.

Pre-freeze (default): forbidden blinding-sensitive paths → exit 2.

Reproduce:
  py scripts/check_mkm_governance_ablation_n80plus_post_freeze_staging_v1.py
  py scripts/check_mkm_governance_ablation_n80plus_post_freeze_staging_v1.py --phase 1
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = (
    ROOT
    / "docs/final/artifacts/mkm_governance_ablation_n80plus_post_freeze_staging_check_v1_latest.json"
)
FREEZE_RECEIPT = (
    ROOT
    / "docs/research/mkm_governance_ablation_n80plus/blind_human_rater/01_PRIMARY_BLIND_FREEZE_RECEIPT.json"
)

ALWAYS_FORBIDDEN = re.compile(
    r"(rater_key_hidden|secondary_ai_review|independent_ai_review_(scores|notes|provenance)|"
    r"AUDIT_PRIORITY_14)",
    re.I,
)
PRE_FREEZE_FORBIDDEN = re.compile(
    r"(rater_key_hidden|rater_worksheet|secondary_ai_review|response_archive/|"
    r"PAIRED_AB_LEDGER|01_RESULT_SEAL|independent_ai_review_)",
    re.I,
)
PHASE1_EXTRA_ALLOWED = re.compile(
    r"(response_archive/|rater_worksheet|01_PRIMARY_BLIND_FREEZE_RECEIPT|PAIRED_AB_LEDGER)",
    re.I,
)


def staged_paths() -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
    )
    return [ln.strip().replace("\\", "/") for ln in out.splitlines() if ln.strip()]


def freeze_complete() -> bool:
    if not FREEZE_RECEIPT.is_file():
        return False
    doc = json.loads(FREEZE_RECEIPT.read_text(encoding="utf-8"))
    return doc.get("primary_blind_freeze_complete") is True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=(1, 2, 3))
    parser.add_argument("--paths-file", type=Path)
    args = parser.parse_args()

    paths = (
        [ln.strip().replace("\\", "/") for ln in args.paths_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if args.paths_file
        else staged_paths()
    )

    violations: list[str] = []
    frozen = freeze_complete()

    for p in paths:
        if ALWAYS_FORBIDDEN.search(p) and args.phase != 3:
            violations.append(p)
            continue
        if args.phase is None and PRE_FREEZE_FORBIDDEN.search(p):
            violations.append(p)
            continue
        if args.phase == 1:
            if not frozen:
                violations.append("FREEZE_RECEIPT_INCOMPLETE")
                break
            if PRE_FREEZE_FORBIDDEN.search(p) and not PHASE1_EXTRA_ALLOWED.search(p):
                if "secondary_ai" in p or "rater_key_hidden" in p:
                    violations.append(p)
            continue
        if args.phase == 2:
            if not frozen:
                violations.append("FREEZE_RECEIPT_INCOMPLETE")
                break
            if "rater_key_hidden" in p:
                violations.append(p)

    violations = sorted(set(violations))
    ok = len(violations) == 0
    report = {
        "ok": ok,
        "phase": args.phase,
        "freeze_complete": frozen,
        "staged_count": len(paths),
        "violations": violations,
    }
    CHECK.parent.mkdir(parents=True, exist_ok=True)
    CHECK.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "violations": violations}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
