#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SUITE = ART / "logos_semantic_query_smoke_suite_latest.json"
DEFAULT_OUT = ART / "logos_semantic_drift_threshold_sweep_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _f(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep low-confidence threshold over semantic query suite.")
    ap.add_argument("--suite-json", type=Path, default=DEFAULT_SUITE)
    ap.add_argument("--thresholds", type=str, default="0.40,0.45,0.50,0.55,0.60")
    ap.add_argument("--target-low-conf-rate-max", type=float, default=0.60)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    suite = args.suite_json if args.suite_json.is_absolute() else ROOT / args.suite_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    if not suite.is_file():
        raise SystemExit(f"Missing suite json: {suite}")

    doc = json.loads(suite.read_text(encoding="utf-8-sig"))
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    ok_scores = [_f(r.get("top_match_cosine")) for r in rows if isinstance(r, dict) and r.get("status") == "ok"]
    ok_scores = [s for s in ok_scores if s is not None]

    try:
        thresholds = [float(x.strip()) for x in args.thresholds.split(",") if x.strip()]
    except ValueError as exc:
        raise SystemExit(f"Invalid thresholds list: {exc}") from exc
    if not thresholds:
        raise SystemExit("No thresholds provided")

    sweep_rows: list[dict[str, Any]] = []
    for th in thresholds:
        low = [s for s in ok_scores if s < th]
        rate = (len(low) / len(ok_scores)) if ok_scores else 1.0
        sweep_rows.append(
            {
                "min_cosine": round(th, 6),
                "samples": len(ok_scores),
                "low_confidence_count": len(low),
                "low_confidence_rate": round(rate, 6),
            }
        )

    target = float(args.target_low_conf_rate_max)
    candidates = [r for r in sweep_rows if float(r["low_confidence_rate"]) <= target]
    recommended = candidates[-1] if candidates else sweep_rows[0]

    result = {
        "schema": "logos_semantic_drift_threshold_sweep_v1",
        "generated_at_utc": _now(),
        "source_suite_json": str(suite.resolve()),
        "target_low_conf_rate_max": round(target, 6),
        "rows": sweep_rows,
        "recommended_min_cosine": recommended["min_cosine"],
        "recommended_row": recommended,
        "decision": "RECOMMENDED_THRESHOLD_FOUND" if candidates else "NO_THRESHOLD_MEETS_TARGET",
        "track_wall": {
            "shadow_only": True,
            "auto_trade_enable": False,
        },
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "recommended_min_cosine": recommended["min_cosine"],
                "decision": result["decision"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

