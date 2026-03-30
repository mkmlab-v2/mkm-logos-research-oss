# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.7, K:0.7, M:0.5}
# Balance: 89
# Purpose: Export daily canary KPI snapshot and rollback decision.
# Keywords: canary, kpi, rollback, compression, monitoring
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
DEFAULT_ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_CANARY_KPI_V1.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bool(condition: bool, reason: str, out: list[str]) -> bool:
    if not condition:
        out.append(reason)
    return condition


def main() -> int:
    ap = argparse.ArgumentParser(description="Export canary KPI snapshot with rollback decision.")
    ap.add_argument("--decision", default=str(DEFAULT_DECISION), help="Decision artifact path")
    ap.add_argument("--active", default=str(DEFAULT_ACTIVE), help="Active report path")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output KPI snapshot path")
    ap.add_argument("--failure-rate-delta-pp", type=float, default=0.0, help="Observed failure-rate delta vs baseline")
    ap.add_argument("--p95-latency-delta-pct", type=float, default=0.0, help="Observed p95 latency delta vs baseline")
    args = ap.parse_args()

    decision = _load_json(Path(args.decision))
    active = _load_json(Path(args.active))
    policy = decision.get("canary_policy", {})
    thr = policy.get("thresholds", {})

    saving = float(active.get("compression_metrics", {}).get("global_token_saving_rate", 0.0))
    jaccard_drop = float(active.get("quality_gate", {}).get("jaccard_drop_pp", 999.0))
    sensitive_integrity = float(active.get("compression_metrics", {}).get("avg_sensitive_integrity", 0.0))
    failure_rate_delta_pp = float(args.failure_rate_delta_pp)
    p95_latency_delta_pct = float(args.p95_latency_delta_pct)

    reasons: list[str] = []
    checks = {
        "saving_rate_ok": _bool(saving >= float(thr.get("saving_rate_min", 0.5)), "saving_rate_below_min", reasons),
        "jaccard_drop_ok": _bool(
            jaccard_drop <= float(thr.get("jaccard_drop_pp_max", 1.5)), "jaccard_drop_above_max", reasons
        ),
        "sensitive_integrity_ok": _bool(
            sensitive_integrity >= float(thr.get("sensitive_integrity_min", 0.999)), "sensitive_integrity_below_min", reasons
        ),
        "failure_rate_ok": _bool(
            failure_rate_delta_pp <= float(thr.get("failure_rate_delta_pp_max", 0.3)), "failure_rate_delta_above_max", reasons
        ),
        "p95_latency_ok": _bool(
            p95_latency_delta_pct <= float(thr.get("p95_latency_delta_pct_max", 15.0)), "p95_latency_delta_above_max", reasons
        ),
    }

    rollback = len(reasons) > 0
    payload = {
        "schema": "multilens_ultra_compression_canary_kpi_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "input_artifacts": {
            "decision": str(Path(args.decision).as_posix()),
            "active": str(Path(args.active).as_posix()),
        },
        "traffic_percent": int(policy.get("traffic_percent", 10)),
        "observed": {
            "global_token_saving_rate": saving,
            "jaccard_drop_pp": jaccard_drop,
            "avg_sensitive_integrity": sensitive_integrity,
            "failure_rate_delta_pp": failure_rate_delta_pp,
            "p95_latency_delta_pct": p95_latency_delta_pct,
        },
        "thresholds": thr,
        "checks": checks,
        "rollback": rollback,
        "rollback_reasons": reasons,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"ROLLBACK: {rollback}")
    if reasons:
        print(f"REASONS: {', '.join(reasons)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
