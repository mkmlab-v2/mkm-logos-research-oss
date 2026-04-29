# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.80, L:0.84, K:0.66, M:0.86}
# Balance: 89
# Purpose: Build emotion-weighted memory events from hybrid inputs.
# Keywords: memory, emotion, valence, arousal, uncertainty, sasang, jsonl
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
BTC_PROJECT_ROOT = WORKSPACE_ROOT / "projects" / "bitcoin-trading"
if str(BTC_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(BTC_PROJECT_ROOT))

from src.analysis.sasang_emotion_bridge import build_emotion_weight


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def _parse_day_from_ts(ts: str) -> str | None:
    try:
        d = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
        return d.isoformat()
    except Exception:
        return None


def _build_label_indexes(path: Path) -> tuple[Dict[str, Dict[str, Any]], Dict[str, float]]:
    idx: Dict[str, Dict[str, Any]] = {}
    day_idx: Dict[str, float] = {}
    for row in _iter_jsonl(path):
        if not isinstance(row, dict):
            continue
        key = str(row.get("event_id") or row.get("seed_event_id") or "").strip()
        if not key:
            continue
        pnl = row.get("forward_pnl_1d")
        if pnl is None:
            continue
        try:
            pnl_v = float(pnl)
        except Exception:
            continue
        idx[key] = {
            "forward_pnl_1d": pnl_v,
            "label_source": row.get("label_source"),
            "label_observed_day": row.get("label_observed_day"),
            "label_observed_ts_utc": row.get("label_observed_ts_utc"),
        }
        day_raw = row.get("label_observed_day")
        if isinstance(day_raw, str) and len(day_raw) == 8 and day_raw.isdigit():
            day = f"{day_raw[:4]}-{day_raw[4:6]}-{day_raw[6:8]}"
            day_idx[day] = pnl_v
    return idx, day_idx


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_fallback_label(
    timestamp_utc: str,
    day_label_index: Dict[str, float],
    max_days: int,
    fallback_mode: str,
) -> float | None:
    if max_days <= 0 or not day_label_index:
        return None
    day_str = _parse_day_from_ts(timestamp_utc)
    if not day_str:
        return None
    try:
        target = datetime.fromisoformat(day_str).date()
    except Exception:
        return None
    best_forward = None
    best_any = None
    for day_k, pnl_v in day_label_index.items():
        try:
            d = datetime.fromisoformat(day_k).date()
        except Exception:
            continue
        delta = (d - target).days
        dist = abs(delta)
        if dist > max_days:
            continue
        if delta >= 1:
            if best_forward is None or delta < best_forward[0]:
                best_forward = (delta, pnl_v)
        if best_any is None or dist < best_any[0]:
            best_any = (dist, pnl_v)
    if best_forward is not None:
        return float(best_forward[1])
    if fallback_mode == "forward_only":
        return None
    return None if best_any is None else float(best_any[1])


def build_memory_event(
    row: Dict[str, Any],
    label_index: Dict[str, Dict[str, Any]],
    day_label_index: Dict[str, float],
    label_fallback_max_days: int,
    label_fallback_mode: str,
) -> Dict[str, Any]:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    panic_ratio = row.get("panic_ratio", metrics.get("panic_ratio"))
    fomo_index = row.get("fomo_index", metrics.get("fomo_index"))
    market_volatility = row.get("market_volatility", metrics.get("market_volatility"))
    emo = build_emotion_weight(
        panic_ratio=panic_ratio,
        fomo_index=fomo_index,
        market_volatility=market_volatility,
        market_sentiment_latent=row.get("market_sentiment_latent"),
        llm_sentiment_score=row.get("llm_sentiment_score"),
    )
    ts = row.get("timestamp_utc") or _now_utc_iso()
    event_id = str(row.get("event_id") or row.get("seed_event_id") or f"emo-{abs(hash(ts))}")
    forward_pnl_1d = row.get("forward_pnl_1d")
    label_meta: Dict[str, Any] = {}
    if forward_pnl_1d is None:
        label_row = label_index.get(event_id)
        if isinstance(label_row, dict):
            forward_pnl_1d = label_row.get("forward_pnl_1d")
            label_meta = {
                "match_mode": "event_id_exact",
                "label_source": label_row.get("label_source"),
                "label_observed_day": label_row.get("label_observed_day"),
                "label_observed_ts_utc": label_row.get("label_observed_ts_utc"),
            }
    if forward_pnl_1d is None:
        forward_pnl_1d = _resolve_fallback_label(
            ts, day_label_index, label_fallback_max_days, label_fallback_mode
        )
        if forward_pnl_1d is not None:
            label_meta = {"match_mode": "day_fallback", "label_source": "day_index_fallback"}

    simulation_meta = row.get("simulation_meta") if isinstance(row.get("simulation_meta"), dict) else {}
    source = (
        row.get("source")
        or simulation_meta.get("engine_name")
        or row.get("source_type")
        or "unknown"
    )

    return {
        "schema_version": "emotion_weighted_memory_event_v1",
        "event_id": event_id,
        "timestamp_utc": ts,
        "source": str(source),
        "emotion": {
            "valence": emo.valence,
            "arousal": emo.arousal,
            "uncertainty": emo.uncertainty,
            "source_mode": emo.source_mode,
            "sasang_axes": {"ae": emo.ae, "no": emo.no, "hui": emo.hui, "rak": emo.rak},
        },
        "quant_inputs": {
            "panic_ratio": panic_ratio,
            "fomo_index": fomo_index,
            "market_volatility": market_volatility,
        },
        "text_inputs": {
            "market_sentiment_latent": row.get("market_sentiment_latent"),
            "llm_sentiment_score": row.get("llm_sentiment_score"),
        },
        "labels": {"forward_pnl_1d": forward_pnl_1d, "meta": label_meta},
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Build emotion-weighted memory events JSONL.")
    p.add_argument("--in-jsonl", type=Path, required=True, help="Input JSONL with quant/text sentiment fields.")
    p.add_argument("--out-jsonl", type=Path, required=True, help="Output event JSONL path.")
    p.add_argument(
        "--labels-jsonl",
        type=Path,
        default=None,
        help="Optional label JSONL with event_id/seed_event_id + forward_pnl_1d",
    )
    p.add_argument(
        "--label-fallback-max-days",
        type=int,
        default=0,
        help="Allow nearest-day label fallback within N days when event_id lookup misses (0=off)",
    )
    p.add_argument(
        "--label-fallback-mode",
        choices=["forward_only", "nearest_any"],
        default="forward_only",
        help="Fallback policy for day-level label match.",
    )
    args = p.parse_args()

    rows = list(_iter_jsonl(args.in_jsonl))
    label_index: Dict[str, Dict[str, Any]] = {}
    day_label_index: Dict[str, float] = {}
    if args.labels_jsonl is not None:
        if not args.labels_jsonl.is_file():
            raise FileNotFoundError(f"labels-jsonl not found: {args.labels_jsonl}")
        label_index, day_label_index = _build_label_indexes(args.labels_jsonl)
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with args.out_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            ev = build_memory_event(
                row,
                label_index,
                day_label_index,
                args.label_fallback_max_days,
                args.label_fallback_mode,
            )
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    print(f"WROTE: {args.out_jsonl} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

