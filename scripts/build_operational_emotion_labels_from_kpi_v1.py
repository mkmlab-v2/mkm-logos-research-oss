#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import argparse

ROOT = Path(__file__).resolve().parents[1]
KPI_DIR = ROOT / "projects" / "bitcoin-trading" / "memory" / "kpi"
TRINITY_BACKFILL_JSONL = (
    ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "risk" / "trinity_predictions_oof_backfill_latest.jsonl"
)
OUT_JSONL = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "emotion" / "operational_emotion_forward_labels_latest.jsonl"


def _file_day(path: Path) -> str | None:
    m = re.match(r"kpi_snapshot_(\d{8})\.jsonl$", path.name)
    return m.group(1) if m else None


def _extract_last_net(path: Path) -> float | None:
    last = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        v = row.get("exchange_snapshot_24h_net")
        if isinstance(v, (int, float)):
            last = float(v)
    return last


def _parse_ts_utc(v: str) -> datetime | None:
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        return None


def _kpi_event_id(ts: datetime) -> str:
    return f"kpi_intraday_{ts.strftime('%Y%m%d%H%M%S')}"


def _iter_kpi_intraday_points(paths: List[Path], step_minutes: int) -> List[Tuple[datetime, float]]:
    points: List[Tuple[datetime, float]] = []
    min_step = max(1, step_minutes)
    last_ts: datetime | None = None
    for p in sorted(paths):
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            ts_raw = str(row.get("ts_utc", "")).strip()
            ts = _parse_ts_utc(ts_raw)
            net = row.get("exchange_snapshot_24h_net")
            if ts is None or not isinstance(net, (int, float)):
                continue
            if last_ts is not None and (ts - last_ts).total_seconds() < (min_step * 60):
                continue
            points.append((ts, float(net)))
            last_ts = ts
    points.sort(key=lambda x: x[0])
    return points


def _build_kpi_intraday_forward_rows(paths: List[Path], step_minutes: int, tolerance_hours: int) -> list[dict]:
    points = _iter_kpi_intraday_points(paths, step_minutes)
    if not points:
        return []
    rows: list[dict] = []
    tolerance = timedelta(hours=max(1, tolerance_hours))
    j = 0
    for i, (ts, _net) in enumerate(points):
        target = ts + timedelta(days=1)
        while j < len(points) and points[j][0] < target - tolerance:
            j += 1
        best_idx = -1
        best_dist = None
        for k in (j, j + 1):
            if 0 <= k < len(points):
                dist = abs(points[k][0] - target)
                if dist <= tolerance and (best_dist is None or dist < best_dist):
                    best_dist = dist
                    best_idx = k
        if best_idx < 0:
            continue
        future_ts, future_net = points[best_idx]
        rows.append(
            {
                "event_id": _kpi_event_id(ts),
                "forward_pnl_1d": float(future_net),
                "label_observed_day": future_ts.date().isoformat(),
                "label_observed_ts_utc": future_ts.isoformat(),
                "label_source": "kpi_snapshot_intraday_nearest_24h_exchange_snapshot_24h_net",
            }
        )
    return rows


def _build_trinity_backfill_forward_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        ts = str(item.get("ts_utc", "")).strip()
        if not ts:
            continue
        target = item.get("target") if isinstance(item.get("target"), dict) else {}
        future = target.get("future_exchange_snapshot_24h_net")
        if not isinstance(future, (int, float)):
            continue
        event_id = "trinity_backfill_" + re.sub(r"[^0-9]", "", ts)[:14]
        if not event_id:
            continue
        rows.append(
            {
                "event_id": event_id,
                "forward_pnl_1d": float(future),
                "label_observed_day": ts[:10],
                "label_source": "trinity_backfill_target_future_exchange_snapshot_24h_net",
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Build forward labels from KPI/trinity for emotion memory.")
    ap.add_argument(
        "--kpi-intraday-step-minutes",
        type=int,
        default=60,
        help="Sampling step for KPI intraday event labels.",
    )
    ap.add_argument(
        "--kpi-forward-tolerance-hours",
        type=int,
        default=6,
        help="Tolerance for nearest +24h KPI label alignment.",
    )
    args = ap.parse_args()

    kpi_paths = sorted(KPI_DIR.glob("kpi_snapshot_*.jsonl"))
    by_day: Dict[str, float] = {}
    for p in kpi_paths:
        day = _file_day(p)
        if not day:
            continue
        net = _extract_last_net(p)
        if net is None:
            continue
        by_day[day] = net

    # Forward label convention:
    # - event_id for day D gets KPI net observed on day D+1.
    # - this avoids same-day leakage and matches "forward_pnl_1d" meaning.
    ordered_days: List[Tuple[str, float]] = sorted(by_day.items())
    forward_rows = []
    for i in range(len(ordered_days) - 1):
        day, _cur_net = ordered_days[i]
        next_day, next_net = ordered_days[i + 1]
        row = {
            "event_id": f"atproto_day_{day}",
            "forward_pnl_1d": next_net,
            "label_observed_day": next_day,
            "label_source": "kpi_snapshot_exchange_snapshot_24h_net",
        }
        forward_rows.append(row)

    forward_rows.extend(
        _build_kpi_intraday_forward_rows(
            kpi_paths,
            step_minutes=args.kpi_intraday_step_minutes,
            tolerance_hours=args.kpi_forward_tolerance_hours,
        )
    )
    forward_rows.extend(_build_trinity_backfill_forward_rows(TRINITY_BACKFILL_JSONL))

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for row in forward_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"WROTE: {OUT_JSONL} ({len(forward_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

