#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS_JSONL = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_market_proxy_events_latest.jsonl"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_transition_leakage_audit_latest.json"


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            yield obj


def _parse_ts(v: str) -> datetime | None:
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit temporal leakage for sasang symptom transition labels.")
    ap.add_argument("--events-jsonl", type=Path, default=DEFAULT_EVENTS_JSONL)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    args = ap.parse_args()

    total = 0
    checked = 0
    leakage = 0
    samples: List[Dict[str, Any]] = []
    for e in _iter_jsonl(args.events_jsonl):
        total += 1
        event_ts = _parse_ts(str(e.get("timestamp_utc", "")))
        labels = e.get("labels") if isinstance(e.get("labels"), dict) else {}
        future_worsened = labels.get("future_worsened")
        if not isinstance(future_worsened, bool):
            continue
        meta = labels.get("meta") if isinstance(labels.get("meta"), dict) else {}
        obs_ts = _parse_ts(str(meta.get("label_observed_ts_utc", "")))
        if event_ts is None or obs_ts is None:
            continue
        checked += 1
        if obs_ts <= event_ts:
            leakage += 1
            if len(samples) < 20:
                samples.append(
                    {
                        "event_id": e.get("event_id"),
                        "event_ts": e.get("timestamp_utc"),
                        "label_observed_ts_utc": meta.get("label_observed_ts_utc"),
                        "label_source": meta.get("label_source"),
                    }
                )

    out = {
        "schema_version": "sasang_symptom_transition_leakage_audit_v1",
        "n_total_events": total,
        "n_checked_events": checked,
        "n_leakage_suspects": leakage,
        "leakage_ratio": (leakage / checked) if checked else 0.0,
        "status": "pass" if leakage == 0 else "fail",
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
        "samples": samples,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
