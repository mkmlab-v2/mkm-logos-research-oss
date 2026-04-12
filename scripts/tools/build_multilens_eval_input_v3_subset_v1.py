#!/usr/bin/env python3
"""Build MULTILENS_PERFORMANCE_EVAL_INPUT_V3.json from V2 by keeping the first N compression_cases (bench subset).

Schema string bumped to multilens_performance_eval_input_v3; same per-case shape as V1/V2.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="src", type=Path, default=ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json")
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V3.json",
    )
    ap.add_argument("--first-n", type=int, default=25, help="Number of compression_cases to keep from the start (default 25).")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    if not src.is_file():
        print(f"FAIL: missing {src}", file=sys.stderr)
        return 1
    doc = json.loads(src.read_text(encoding="utf-8"))
    cases = doc.get("compression_cases") or []
    if not isinstance(cases, list) or not cases:
        print("FAIL: no compression_cases", file=sys.stderr)
        return 1
    n = max(1, int(args.first_n))
    sub = cases[:n]
    out_doc = {
        "schema": "multilens_performance_eval_input_v3",
        "description": (
            f"V3 subset of V2 for routing / v4 sensitivity tests: first {len(sub)} compression_cases only. "
            "Not a replacement for full V2 governance benches."
        ),
        "compression_cases": sub,
        "source_derived_from": str(src.relative_to(ROOT)).replace("\\", "/"),
        "subset_first_n": len(sub),
    }
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out} cases={len(sub)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
