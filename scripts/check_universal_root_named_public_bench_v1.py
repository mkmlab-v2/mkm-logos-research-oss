#!/usr/bin/env python3
"""Check UR-B0-MISS-HOLDOUT-v1 named public mini-bench [HYPO · HOLD]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.universal_root_public_push_gate_lib_v1 import evaluate_named_public_bench  # noqa: E402

OUT = ROOT / "reports/universal_root_named_public_bench_check_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true", help="exit 1 unless named_public_bench_ok")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    ev = evaluate_named_public_bench()
    doc = {**ev, "reproduce": "py scripts/check_universal_root_named_public_bench_v1.py --strict"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ev["named_public_bench_ok"], "pair_count": ev.get("pair_count"), "out": str(args.out)}))
    return 0 if ev["named_public_bench_ok"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
