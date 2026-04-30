from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Guard check for MKM AI final ops bundle."
    )
    parser.add_argument("--workspace-root", default="C:/workspace")
    parser.add_argument("--min-pass-rate", type=float, default=95.0)
    parser.add_argument("--min-sample-count", type=int, default=3)
    return parser.parse_args()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def main() -> int:
    args = _parse_args()
    root = Path(args.workspace_root)
    bundle_path = root / "docs" / "final" / "artifacts" / "mkm_ai_final_ops_bundle_latest.json"
    bundle = _read_json(bundle_path)

    if not bundle:
        print(f"FAIL: missing or invalid bundle: {bundle_path}")
        return 1

    status = str(bundle.get("status", ""))
    is_final = bool(bundle.get("is_final", False))
    decision = str(bundle.get("promotion_decision", ""))
    promotion_ready = bool(bundle.get("promotion_ready", False))
    readiness_ok = bool(bundle.get("readiness_overall_passed", False))
    pass_rate = float(bundle.get("weekly_pass_rate_percent", 0.0) or 0.0)
    sample_count = int(bundle.get("weekly_sample_count", 0) or 0)

    failures = []
    if status != "APPROVED_FINAL_V2":
        failures.append(f"status={status}")
    if not is_final:
        failures.append("is_final=false")
    if decision != "GO_FINAL_V2":
        failures.append(f"promotion_decision={decision}")
    if not promotion_ready:
        failures.append("promotion_ready=false")
    if not readiness_ok:
        failures.append("readiness_overall_passed=false")
    if pass_rate < float(args.min_pass_rate):
        failures.append(f"weekly_pass_rate_percent={pass_rate}<{args.min_pass_rate}")
    if sample_count < int(args.min_sample_count):
        failures.append(f"weekly_sample_count={sample_count}<{args.min_sample_count}")

    if failures:
        print("FINAL OPS GUARD: FAIL")
        print("; ".join(failures))
        return 1

    print("FINAL OPS GUARD: PASS")
    print(
        f"status={status} decision={decision} pass_rate={pass_rate} sample_count={sample_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
