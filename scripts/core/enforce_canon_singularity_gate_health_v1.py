#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Enforce policy on canon gate health summary.")
    ap.add_argument(
        "--health-summary-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_health_summary_v1.json",
    )
    ap.add_argument("--max-fail-count", type=int, default=0)
    ap.add_argument("--min-pass-rate", type=float, default=1.0)
    ap.add_argument("--allow-yellow", action="store_true")
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_policy_eval_v1.json",
    )
    args = ap.parse_args()

    data = _read_json(Path(args.health_summary_json))
    counts = data.get("counts", {})
    fail_count = int(counts.get("fail_count", 0))
    pass_rate = float(counts.get("pass_rate", 0.0))
    health_level = str(data.get("health_level") or "unknown")

    reasons: list[str] = []
    if fail_count > int(args.max_fail_count):
        reasons.append(f"fail_count {fail_count} > max_fail_count {int(args.max_fail_count)}")
    if pass_rate < float(args.min_pass_rate):
        reasons.append(f"pass_rate {pass_rate:.4f} < min_pass_rate {float(args.min_pass_rate):.4f}")
    if (not args.allow_yellow) and health_level == "yellow":
        reasons.append("health_level is yellow while allow_yellow is false")
    if health_level == "red":
        reasons.append("health_level is red")

    ok = len(reasons) == 0
    out = {
        "schema": "original_corpus_regime_singularity_canon_quality_gate_policy_eval_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "health_summary_json": str(args.health_summary_json),
            "max_fail_count": int(args.max_fail_count),
            "min_pass_rate": float(args.min_pass_rate),
            "allow_yellow": bool(args.allow_yellow),
        },
        "status": "pass" if ok else "fail",
        "health_level": health_level,
        "fail_count": fail_count,
        "pass_rate": round(pass_rate, 4),
        "reasons": reasons,
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if ok:
        print("OK: canon gate health policy pass")
        return 0
    print("FAIL: canon gate health policy fail", file=sys.stderr)
    for r in reasons:
        print(f"- {r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

