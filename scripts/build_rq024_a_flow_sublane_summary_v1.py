#!/usr/bin/env python3
"""[NON_GATING] RQ-024-A: summarize KOSPI flow probe + gap audit into sublane charter patch."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CHARTER = ROOT / "docs/final/artifacts/rq024_kospi_flow_proxy_sublane_a_v1.json"
DEFAULT_PROBE = ROOT / "reports/kospi_prophecy_miss_flow_probe_v1_latest.json"
DEFAULT_GAPS = ROOT / "reports/kospi_daily_flow_gaps_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq024_a_flow_sublane_summary_v1_latest.json"
SCHEMA = "rq024_a_flow_sublane_summary_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--charter-json", type=Path, default=DEFAULT_CHARTER)
    ap.add_argument("--probe-json", type=Path, default=DEFAULT_PROBE)
    ap.add_argument("--gaps-json", type=Path, default=DEFAULT_GAPS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-charter", action="store_true", help="Merge summary into charter JSON")
    args = ap.parse_args(argv)

    charter_path = args.charter_json if args.charter_json.is_absolute() else ROOT / args.charter_json
    probe = _load(args.probe_json if args.probe_json.is_absolute() else ROOT / args.probe_json)
    gaps = _load(args.gaps_json if args.gaps_json.is_absolute() else ROOT / args.gaps_json)

    miss_days = int(probe.get("miss_day_count") or probe.get("miss_days") or 0)
    daily_hits = int(probe.get("miss_days_with_daily_flow") or probe.get("daily_hits") or 0)
    data_gaps = probe.get("data_gaps") or gaps.get("missing_dates") or []
    missing_n = int(gaps.get("missing_n") or len(data_gaps) if isinstance(data_gaps, list) else 0)

    summary: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "gating": "[NON_GATING]",
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024-A",
        "parent_rq": "RQ-024",
        "probe": {
            "path": str((args.probe_json if args.probe_json.is_absolute() else ROOT / args.probe_json).relative_to(ROOT)).replace("\\", "/"),
            "miss_days": miss_days,
            "daily_hits": daily_hits,
            "hit_rate_daily": round(daily_hits / miss_days, 6) if miss_days else None,
            "data_gaps": data_gaps,
        },
        "gap_audit": {
            "path": str((args.gaps_json if args.gaps_json.is_absolute() else ROOT / args.gaps_json).relative_to(ROOT)).replace("\\", "/"),
            "missing_n": missing_n,
        },
        "dod_sublane_a": {
            "csv_join_ok": missing_n == 0,
            "probe_written": bool(probe),
            "combined_055_claim": False,
            "merge_into_btc_lens_promotion": False,
        },
        "operator_note": "Flow proxy is observation-only; do not merge into BTC lens 0.52 / Track A claims.",
    }

    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")

    if args.write_charter and charter_path.is_file():
        charter = _load(charter_path)
        charter["last_probe_summary"] = {
            "generated_at_utc": summary["generated_at_utc"],
            "miss_days": miss_days,
            "daily_hits": daily_hits,
            "missing_n": missing_n,
            "summary_json": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        }
        charter["status"] = "OPEN"
        charter_path.write_text(json.dumps(charter, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"UPDATED: {charter_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
