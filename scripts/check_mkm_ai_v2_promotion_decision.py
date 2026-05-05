from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decide MKM AI v2 final promotion status from readiness artifacts."
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

    readiness_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_readiness_latest.json"
    weekly_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_weekly_readiness_report_latest.json"
    out_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_promotion_decision_latest.json"

    readiness = _read_json(readiness_path)
    weekly = _read_json(weekly_path)

    readiness_ok = bool(readiness.get("overall_passed"))
    pass_rate = float(weekly.get("pass_rate_percent", 0.0) or 0.0)
    sample_count = int(weekly.get("sample_count", 0) or 0)

    pass_rate_ok = pass_rate >= float(args.min_pass_rate)
    sample_ok = sample_count >= int(args.min_sample_count)

    promotion_ready = readiness_ok and pass_rate_ok and sample_ok
    decision = "GO_FINAL_V2" if promotion_ready else "HOLD_OPERATIONAL_V1"

    reasons = []
    if not readiness_ok:
        reasons.append("readiness overall_passed is false")
    if not pass_rate_ok:
        reasons.append(
            f"weekly pass_rate_percent {pass_rate} below threshold {args.min_pass_rate}"
        )
    if not sample_ok:
        reasons.append(
            f"weekly sample_count {sample_count} below minimum {args.min_sample_count}"
        )
    if not reasons:
        reasons.append("all promotion gates satisfied")

    payload = {
        "schema": "mkm_ai_v2_promotion_decision_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "readiness_path": str(readiness_path),
            "weekly_report_path": str(weekly_path),
            "min_pass_rate": float(args.min_pass_rate),
            "min_sample_count": int(args.min_sample_count),
        },
        "metrics": {
            "readiness_overall_passed": readiness_ok,
            "weekly_pass_rate_percent": pass_rate,
            "weekly_sample_count": sample_count,
        },
        "decision": decision,
        "promotion_ready": promotion_ready,
        "reasons": reasons,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"promotion decision written: {out_path}")
    print(f"decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
