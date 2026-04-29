#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List
import argparse

ROOT = Path(__file__).resolve().parents[1]
ATPROTO_DIR = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "btrack" / "raw_feeds" / "atproto"
KPI_DIR = ROOT / "projects" / "bitcoin-trading" / "memory" / "kpi"
TRINITY_BACKFILL_JSONL = (
    ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "risk" / "trinity_predictions_oof_backfill_latest.jsonl"
)
OUT_JSONL = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "emotion" / "operational_sentiment_daily_latest.jsonl"

PANIC_TERMS = ("panic", "fear", "crash", "plunge", "dump", "sell pressure", "투매", "공포", "급락")
FOMO_TERMS = ("fomo", "euphoria", "surge", "all-time high", "bullish", "매수", "급등", "상승")
NOISE_TERMS = ("onlyfans", "cammodels", "live sex", "#nsfw", "fucky.mom")


def _iter_jsonl(path: Path) -> Iterable[dict]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except Exception:
            continue


def _file_day(path: Path) -> str | None:
    m = re.match(r"(\d{8})_atproto_sentiment_raw\.jsonl$", path.name)
    return m.group(1) if m else None


def _filter_atproto_paths_by_lookback(paths: List[Path], lookback_days: int) -> List[Path]:
    if lookback_days <= 0:
        return paths
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=lookback_days - 1))
    filtered: List[Path] = []
    for p in paths:
        day = _file_day(p)
        if not day:
            continue
        try:
            d = datetime.strptime(day, "%Y%m%d").date()
        except Exception:
            continue
        if d >= cutoff:
            filtered.append(p)
    return filtered


def _score_text(text: str) -> str:
    t = text.lower()
    has_panic = any(k in t for k in PANIC_TERMS)
    has_fomo = any(k in t for k in FOMO_TERMS)
    if has_panic and not has_fomo:
        return "panic"
    if has_fomo and not has_panic:
        return "fomo"
    return "neutral"


def _is_noise(text: str) -> bool:
    t = text.lower()
    if any(k in t for k in NOISE_TERMS):
        return True
    # repetitive low-information ticker spam heuristic
    if t.count("#bitcoin") >= 3 and len(t) < 120:
        return True
    return False


def build_rows(paths: List[Path]) -> List[dict]:
    rows: List[dict] = []
    for p in sorted(paths):
        day = _file_day(p)
        if not day:
            continue
        panic = 0
        fomo = 0
        neutral = 0
        total = 0
        for item in _iter_jsonl(p):
            text = str(item.get("text", "")).strip()
            if not text or _is_noise(text):
                continue
            cls = _score_text(text)
            total += 1
            if cls == "panic":
                panic += 1
            elif cls == "fomo":
                fomo += 1
            else:
                neutral += 1
        if total == 0:
            continue
        panic_ratio = panic / total
        fomo_index = fomo / total
        consensus_strength = max(panic_ratio, fomo_index, neutral / total)
        rows.append(
            {
                "timestamp_utc": f"{day[:4]}-{day[4:6]}-{day[6:8]}T00:00:00Z",
                "seed_event_id": f"atproto_day_{day}",
                "seed_cutoff_time": datetime.now(timezone.utc).isoformat(),
                "metrics": {
                    "panic_ratio": round(panic_ratio, 6),
                    "fomo_index": round(fomo_index, 6),
                    "consensus_strength": round(consensus_strength, 6),
                },
                "simulation_meta": {
                    "engine_name": "atproto_operational_heuristic_v1",
                    "agent_count": total,
                    "prompt_hash": "sha256:operational-atproto-v1",
                },
            }
        )
    return rows


def _iter_last_json(path: Path) -> dict | None:
    last = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            last = json.loads(line)
        except Exception:
            continue
    return last


def _kpi_day(path: Path) -> str | None:
    m = re.match(r"kpi_snapshot_(\d{8})\.jsonl$", path.name)
    return m.group(1) if m else None


def _parse_ts_utc(v: str) -> datetime | None:
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        return None


def _iter_kpi_rows(path: Path) -> Iterable[dict]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            yield row


def _kpi_event_id(ts: datetime) -> str:
    return f"kpi_intraday_{ts.strftime('%Y%m%d%H%M%S')}"


def build_rows_from_kpi(paths: List[Path], existing_ids: set[str], intraday_step_minutes: int) -> List[dict]:
    rows: List[dict] = []
    last_emitted_ts: datetime | None = None
    min_step = max(1, intraday_step_minutes)
    for p in sorted(paths):
        for item in _iter_kpi_rows(p):
            ts_raw = str(item.get("ts_utc", "")).strip()
            ts = _parse_ts_utc(ts_raw)
            if ts is None:
                continue
            if last_emitted_ts is not None and (ts - last_emitted_ts).total_seconds() < (min_step * 60):
                continue
            core = item.get("mkm_singular_core") if isinstance(item.get("mkm_singular_core"), dict) else {}
            buy_ratio = float(core.get("buy_ratio", 0.0) or 0.0)
            sell_ratio = float(core.get("sell_ratio", 0.0) or 0.0)
            locked_ratio = float(core.get("locked_ratio", 1.0) or 1.0)
            panic_ratio = max(0.0, min(1.0, sell_ratio))
            fomo_index = max(0.0, min(1.0, buy_ratio))
            consensus_strength = max(panic_ratio, fomo_index, max(0.0, min(1.0, locked_ratio)))
            event_id = _kpi_event_id(ts)
            if event_id in existing_ids:
                continue
            rows.append(
                {
                    "timestamp_utc": ts.isoformat(),
                    "seed_event_id": event_id,
                    "seed_cutoff_time": datetime.now(timezone.utc).isoformat(),
                    "metrics": {
                        "panic_ratio": round(panic_ratio, 6),
                        "fomo_index": round(fomo_index, 6),
                        "consensus_strength": round(consensus_strength, 6),
                    },
                    "simulation_meta": {
                        "engine_name": "kpi_derived_sentiment_proxy_v1",
                        "agent_count": 1,
                        "prompt_hash": "sha256:kpi-derived-sentiment-v1",
                    },
                }
            )
            last_emitted_ts = ts
    return rows


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


def build_rows_from_trinity_backfill(path: Path, existing_ids: set[str]) -> List[dict]:
    if not path.exists():
        return []
    rows: List[dict] = []
    for item in _iter_jsonl(path):
        ts = str(item.get("ts_utc", "")).strip()
        if not ts:
            continue
        event_id = "trinity_backfill_" + re.sub(r"[^0-9]", "", ts)[:14]
        if not event_id or event_id in existing_ids:
            continue
        gov = item.get("trinity_governor") if isinstance(item.get("trinity_governor"), dict) else {}
        logos = float(gov.get("logos_regime_score", 0.5) or 0.5)
        myeongri = float(gov.get("myeongri_timing_score", 0.5) or 0.5)
        sasang = float(gov.get("sasang_response_score", 0.5) or 0.5)
        # Keep trinity backfill as a weak proxy lane to avoid overpowering primary atproto/kpi signals.
        fomo_index = _clip01((logos + myeongri) * 0.5)
        panic_ratio = _clip01((1.0 - fomo_index) * (1.0 - 0.25 * sasang))
        consensus_strength = _clip01(max(fomo_index, panic_ratio))
        rows.append(
            {
                "timestamp_utc": ts,
                "seed_event_id": event_id,
                "seed_cutoff_time": datetime.now(timezone.utc).isoformat(),
                "metrics": {
                    "panic_ratio": round(panic_ratio, 6),
                    "fomo_index": round(fomo_index, 6),
                    "consensus_strength": round(consensus_strength, 6),
                },
                "simulation_meta": {
                    "engine_name": "trinity_backfill_sentiment_proxy_v1",
                    "agent_count": 1,
                    "prompt_hash": "sha256:trinity-backfill-sentiment-v1",
                },
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Build operational emotion inputs from atproto+kpi(+optional trinity).")
    ap.add_argument(
        "--atproto-lookback-days",
        type=int,
        default=0,
        help="Use only recent N days of atproto raw files (0=all available).",
    )
    ap.add_argument(
        "--kpi-intraday-step-minutes",
        type=int,
        default=60,
        help="Sampling step for KPI-derived intraday sentiment rows.",
    )
    args = ap.parse_args()

    atproto_files = list(ATPROTO_DIR.glob("*_atproto_sentiment_raw.jsonl"))
    atproto_files = _filter_atproto_paths_by_lookback(atproto_files, args.atproto_lookback_days)
    rows = build_rows(atproto_files)
    existing_ids = {str(r.get("seed_event_id", "")) for r in rows}
    kpi_files = list(KPI_DIR.glob("kpi_snapshot_*.jsonl"))
    rows.extend(build_rows_from_kpi(kpi_files, existing_ids, args.kpi_intraday_step_minutes))
    existing_ids = {str(r.get("seed_event_id", "")) for r in rows}
    rows.extend(build_rows_from_trinity_backfill(TRINITY_BACKFILL_JSONL, existing_ids))
    rows = sorted(rows, key=lambda r: str(r.get("timestamp_utc", "")))
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"WROTE: {OUT_JSONL} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

