#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prune noisy ijeoma_harvest terms from scm_boming_jiju_lexicon_v1.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.prune_scm_boming_jiju_ijeoma_harvest_v1 import apply_prune, plan_prune  # noqa: E402

REPORT_DEFAULT = ROOT / "reports" / "scm_boming_jiju_lexicon_prune_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-priority-keep", type=int, default=50)
    ap.add_argument("--out-json", type=Path, default=REPORT_DEFAULT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    plan = plan_prune(min_priority_keep=args.min_priority_keep)
    if args.apply or args.dry_run:
        plan = apply_prune(plan, dry_run=args.dry_run or not args.apply)

    clean = {k: v for k, v in plan.items() if not str(k).startswith("_")}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(args.out_json), "counts": clean.get("counts")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
