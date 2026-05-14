# Keywords: stt_routing_audit_log_v1, rollup, Silver STT audit
"""Summarize append-only STT routing audit JSONL into a small JSON for dashboards."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _rollup(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_route = Counter(str(r.get("route") or "") for r in rows)
    vendor_latencies = [
        int(r["latency_ms"])
        for r in rows
        if r.get("route") == "vendor" and isinstance(r.get("latency_ms"), int)
    ]
    audio_sum = sum(int(r.get("audio_duration_ms") or 0) for r in rows)
    audio_by_route: Dict[str, int] = {}
    for r in rows:
        rt = str(r.get("route") or "")
        audio_by_route[rt] = audio_by_route.get(rt, 0) + int(r.get("audio_duration_ms") or 0)
    p95: float | None = None
    vendor_latency_ms_avg: float | None = None
    if vendor_latencies:
        vendor_latencies.sort()
        idx = max(0, int(round(0.95 * (len(vendor_latencies) - 1))))
        p95 = float(vendor_latencies[idx])
        vendor_latency_ms_avg = round(sum(vendor_latencies) / len(vendor_latencies), 3)
    n = len(rows)
    vendor_events = int(by_route.get("vendor", 0))
    vendor_share_by_event_pct: float | None = None
    if n > 0:
        vendor_share_by_event_pct = round(100.0 * vendor_events / n, 4)
    times: List[str] = []
    for r in rows:
        t = r.get("occurred_at_utc")
        if isinstance(t, str) and t.strip():
            times.append(t.strip())
    return {
        "schema": "stt_routing_audit_log_v1_summary",
        "generated_at_utc": _utc_now_z(),
        "source_jsonl_rel": None,
        "rows_total": n,
        "route_counts": dict(by_route),
        "audio_duration_ms_sum": audio_sum,
        "audio_duration_ms_by_route": audio_by_route,
        "vendor_rows": vendor_events,
        "vendor_share_by_event_pct": vendor_share_by_event_pct,
        "vendor_latency_ms_avg": vendor_latency_ms_avg,
        "vendor_latency_ms_p95": p95,
        "occurred_at_utc_earliest": min(times) if times else None,
        "occurred_at_utc_latest": max(times) if times else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", type=Path, default=ROOT / "reports" / "stt_routing_audit_log_v1.jsonl")
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports" / "stt_routing_audit_log_v1_summary_latest.json",
    )
    args = ap.parse_args()
    rows = _load_rows(args.in_path)
    doc = _rollup(rows)
    try:
        doc["source_jsonl_rel"] = str(args.in_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        doc["source_jsonl_rel"] = str(args.in_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(args.out), "rows_total": doc["rows_total"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
