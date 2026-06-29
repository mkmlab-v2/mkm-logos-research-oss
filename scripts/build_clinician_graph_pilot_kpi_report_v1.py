#!/usr/bin/env python3
"""Build clinician graph pilot KPI summary from review-feedback JSONL + hub telemetry."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_ts_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _safe_div(a: float, b: float) -> float:
    if b <= 0:
        return 0.0
    return a / b


def _resolve_first_existing(root: Path, candidates: list[str]) -> Path | None:
    for rel in candidates:
        path = root / rel
        if path.is_file():
            return path
    return None


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return float(statistics.quantiles(values, n=100)[max(0, min(98, int(pct) - 1))])


def _load_feedback(path: Path, lower: datetime) -> dict[str, Any]:
    counts = {"up": 0, "down": 0, "hold": 0, "total": 0}
    signoff_count = 0
    conflict_review_count = 0
    encounters: set[str] = set()
    parse_errors = 0
    skipped = 0

    if not path.is_file():
        return {
            "source_path": None,
            "counts": counts,
            "signoff_count": 0,
            "conflict_review_count": 0,
            "unique_encounters": 0,
            "approval_rate": 0.0,
            "parse_errors": 0,
            "skipped_out_of_window": 0,
        }

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        ts = _parse_ts_utc(row.get("ts"))
        if ts and ts < lower:
            skipped += 1
            continue
        fb = str(row.get("feedback") or "").strip().lower()
        if fb in counts:
            counts[fb] += 1
            counts["total"] += 1
        enc = str(row.get("encounter_ref") or "").strip()
        if enc:
            encounters.add(enc)
        reason = str(row.get("reason_code") or "").strip()
        if reason == "physician_signoff_checklist":
            signoff_count += 1
        if reason == "conflict_group_review":
            conflict_review_count += 1

    actionable = counts["up"] + counts["down"] + counts["hold"]
    return {
        "source_path": str(path),
        "counts": counts,
        "signoff_count": signoff_count,
        "conflict_review_count": conflict_review_count,
        "unique_encounters": len(encounters),
        "approval_rate": round(_safe_div(counts["up"], actionable), 4),
        "parse_errors": parse_errors,
        "skipped_out_of_window": skipped,
    }


def _load_telemetry(path: Path, lower: datetime) -> dict[str, Any]:
    event_counts: dict[str, int] = {}
    review_durations: list[float] = []
    signoff_durations: list[float] = []
    parse_errors = 0
    skipped = 0

    if not path.is_file():
        return {
            "source_path": None,
            "event_counts": {},
            "review_timing_ms": {},
            "parse_errors": 0,
            "skipped_out_of_window": 0,
        }

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        ts = _parse_ts_utc(row.get("ts_utc"))
        if ts and ts < lower:
            skipped += 1
            continue
        event = str(row.get("event") or "")
        if not event.startswith("clinician_graph_"):
            continue
        event_counts[event] = event_counts.get(event, 0) + 1
        if event == "clinician_graph_review_timing_v1":
            d_graph = row.get("duration_since_graph_build_ms")
            d_cds = row.get("duration_since_cds_ready_ms")
            if isinstance(d_graph, (int, float)) and d_graph >= 0:
                signoff_durations.append(float(d_graph))
            if isinstance(d_cds, (int, float)) and d_cds >= 0:
                review_durations.append(float(d_cds))

    def timing_stats(values: list[float]) -> dict[str, Any]:
        if not values:
            return {"count": 0}
        return {
            "count": len(values),
            "median_ms": round(statistics.median(values), 1),
            "mean_ms": round(statistics.mean(values), 1),
            "p90_ms": round(_percentile(values, 90) or 0.0, 1),
        }

    return {
        "source_path": str(path),
        "event_counts": event_counts,
        "review_timing_ms": {
            "cds_ready_to_signoff": timing_stats(review_durations),
            "graph_build_to_signoff": timing_stats(signoff_durations),
        },
        "parse_errors": parse_errors,
        "skipped_out_of_window": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument(
        "--feedback-jsonl",
        default="",
        help="override feedback jsonl path",
    )
    parser.add_argument(
        "--telemetry-jsonl",
        default="",
        help="override hub telemetry jsonl path",
    )
    parser.add_argument(
        "--out-json",
        default="docs/final/artifacts/clinician_graph_pilot_kpi_latest.json",
    )
    args = parser.parse_args()

    root = _root()
    now = datetime.now(timezone.utc)
    lower = now - timedelta(days=max(1, args.window_days))

    feedback_path = (
        Path(args.feedback_jsonl)
        if args.feedback_jsonl
        else _resolve_first_existing(
            root,
            [
                "projects/no1kmedi/reports/clinician_graph_review_feedback_v1.jsonl",
                "reports/clinician_graph_review_feedback_v1.jsonl",
            ],
        )
    )
    telemetry_path = (
        Path(args.telemetry_jsonl)
        if args.telemetry_jsonl
        else _resolve_first_existing(
            root,
            [
                "projects/no1kmedi/memory/commercialization/hub_events.jsonl",
                "memory/commercialization/hub_events.jsonl",
            ],
        )
    )

    feedback = _load_feedback(feedback_path, lower) if feedback_path else _load_feedback(Path("__missing__"), lower)
    telemetry = _load_telemetry(telemetry_path, lower) if telemetry_path else _load_telemetry(Path("__missing__"), lower)

    doc = {
        "schema": "clinician_graph_pilot_kpi_summary_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "window_days": args.window_days,
        "research_only": True,
        "send_gate": "HOLD",
        "kpi_headline": {
            "physician_approval_rate": feedback["approval_rate"],
            "signoff_events": feedback["signoff_count"],
            "conflict_reviews": feedback["conflict_review_count"],
            "unique_encounters": feedback["unique_encounters"],
            "graph_build_events": telemetry["event_counts"].get("clinician_graph_build_v1", 0),
            "median_review_ms": telemetry["review_timing_ms"]
            .get("cds_ready_to_signoff", {})
            .get("median_ms"),
        },
        "feedback": feedback,
        "telemetry": telemetry,
        "boundary": {
            "physician_confirmation_required": True,
            "not_standalone_diagnosis": True,
            "internal_pilot_only": True,
        },
    }

    out = root / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "approval_rate": feedback["approval_rate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
