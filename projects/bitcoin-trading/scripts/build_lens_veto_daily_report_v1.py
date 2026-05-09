#!/usr/bin/env python3
"""Build daily lens-veto summary report for Aroon live engine."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(v: Any) -> datetime | None:
    if not isinstance(v, str) or not v:
        return None
    s = v.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        t = line.strip()
        if not t:
            continue
        try:
            obj = json.loads(t)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Daily lens veto report from lens_gate_events jsonl.")
    ap.add_argument(
        "--events-jsonl",
        type=Path,
        default=Path("/opt/bitcoin-trading-live/logs/lens_gate_events.jsonl"),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("/opt/bitcoin-trading-live/docs/final/artifacts/lens_veto_daily_report_latest.json"),
    )
    ap.add_argument(
        "--out-md",
        type=Path,
        default=Path("/opt/bitcoin-trading-live/docs/final/artifacts/lens_veto_daily_report_latest.md"),
    )
    ap.add_argument("--lookback-hours", type=float, default=24.0)
    args = ap.parse_args(argv)

    now = _utc_now()
    cutoff = now - timedelta(hours=max(1.0, float(args.lookback_hours)))
    rows = _read_jsonl(args.events_jsonl)
    window: list[dict[str, Any]] = []
    for r in rows:
        ts = _parse_ts(r.get("timestamp"))
        if ts is None or ts < cutoff:
            continue
        window.append(r)

    total = len(window)
    veto_rows = [r for r in window if str(r.get("signal") or "") == "HOLD_LENS_VETO"]
    veto_count = len(veto_rows)

    long_veto = 0
    short_veto = 0
    confs: list[float] = []
    for r in veto_rows:
        gate = r.get("lens_gate") if isinstance(r.get("lens_gate"), dict) else {}
        target_before = str(gate.get("target_before") or "")
        if target_before == "LONG":
            long_veto += 1
        elif target_before == "SHORT":
            short_veto += 1
        try:
            confs.append(float(gate.get("lens_confidence") or 0.0))
        except (TypeError, ValueError):
            pass

    avg_conf = (sum(confs) / len(confs)) if confs else 0.0
    veto_rate = (veto_count / total) if total > 0 else 0.0

    payload = {
        "schema": "lens_veto_daily_report_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": True,
        "window": {
            "lookback_hours": float(args.lookback_hours),
            "cutoff_utc": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "events_path": str(args.events_jsonl),
            "events_total_window": total,
        },
        "veto": {
            "veto_count": veto_count,
            "veto_rate": round(veto_rate, 6),
            "long_entry_veto_count": long_veto,
            "short_entry_veto_count": short_veto,
            "avg_lens_confidence": round(avg_conf, 6),
        },
        "impact_proxy_note": "This report tracks veto frequency/side only; direct PnL attribution requires separate counterfactual backtest.",
    }
    _write(args.out, payload)

    md = [
        "# Lens Veto Daily Report",
        "",
        f"- generated_at_utc: {payload['generated_at_utc']}",
        f"- window_hours: {args.lookback_hours}",
        f"- events_total_window: {total}",
        f"- veto_count: {veto_count}",
        f"- veto_rate: {payload['veto']['veto_rate']}",
        f"- long_entry_veto_count: {long_veto}",
        f"- short_entry_veto_count: {short_veto}",
        f"- avg_lens_confidence: {payload['veto']['avg_lens_confidence']}",
        "",
        f"- note: {payload['impact_proxy_note']}",
        "",
    ]
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
