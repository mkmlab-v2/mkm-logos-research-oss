#!/usr/bin/env python3
"""Generate Top5 CEE lambda imbalance report with lane cross-map."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
LANE_DSS = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_lane_dss_priority_latest.jsonl"
LANE_MIXED = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_lane_mixed_latest.jsonl"
LANE_APO = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_lane_apocrypha_priority_latest.jsonl"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "cee_lambda_top5_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path):
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if isinstance(obj, dict):
                yield obj


def _lane_symbols(dss_path: Path, mixed_path: Path, apo_path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for lane, p in (("dss_priority", dss_path), ("mixed", mixed_path), ("apocrypha_priority", apo_path)):
        for row in _iter_jsonl(p) or []:
            sym = str(row.get("symbol", "")).strip().lower()
            if sym and sym not in out:
                out[sym] = lane
    return out


def _tokenize(text: str) -> list[str]:
    import re

    return [x.lower() for x in re.findall(r"[A-Za-z0-9_가-힣\u0590-\u05FF]+", text)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Report top5 CEE lambda imbalance")
    ap.add_argument("--active-report", default=str(ACTIVE))
    ap.add_argument("--lane-dss", default=str(LANE_DSS))
    ap.add_argument("--lane-mixed", default=str(LANE_MIXED))
    ap.add_argument("--lane-apocrypha", default=str(LANE_APO))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    active_path = _abs(args.active_report)
    out_path = _abs(args.out)
    if not active_path.is_file():
        print(f"ERROR: missing active report: {active_path}")
        return 2

    lane_map = _lane_symbols(_abs(args.lane_dss), _abs(args.lane_mixed), _abs(args.lane_apocrypha))
    active = _jread(active_path)
    comp_cases = active.get("compression_metrics", {}).get("cases", [])
    rows: list[dict[str, Any]] = []
    for c in comp_cases:
        if not isinstance(c, dict):
            continue
        cee = c.get("cee_core")
        if not isinstance(cee, dict):
            continue
        raw_text = str(c.get("raw_text", "")) if "raw_text" in c else ""
        if not raw_text:
            # fallback: approximate with reconstructed text when raw not present
            raw_text = str(c.get("reconstructed_text_effective", ""))
        tokens = _tokenize(raw_text)
        lanes = sorted({lane_map[t] for t in tokens if t in lane_map})
        rows.append(
            {
                "id": c.get("id"),
                "lambda_deviation": float(cee.get("lambda_deviation", 0.0) or 0.0),
                "state_id": cee.get("state_id"),
                "balance_band": cee.get("metadata_post_it", {}).get("balance_band"),
                "lane_hits": lanes,
            }
        )

    rows.sort(key=lambda x: float(x["lambda_deviation"]), reverse=True)
    top5 = rows[:5]
    uniq = sorted({round(float(r["lambda_deviation"]), 12) for r in rows})
    low_variance = len(uniq) <= 1

    report = {
        "schema": "cee_lambda_top5_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_active_report": str(active_path),
        "sample_count": len(rows),
        "unique_lambda_values": uniq,
        "low_variance_flag": low_variance,
        "top5": top5,
        "interpretation_note": (
            "All cases share same lambda_deviation; ranking is non-discriminative."
            if low_variance
            else "Ranking provides discriminative imbalance candidates."
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: CEE lambda top5 report generated")
    print(f"out={out_path}")
    print(f"sample_count={len(rows)} low_variance={low_variance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
