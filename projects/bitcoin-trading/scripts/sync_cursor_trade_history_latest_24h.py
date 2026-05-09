#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.8, K:0.5, M:0.6}
# Balance: 90
# Purpose: Sync cursor trade history files and regenerate latest 24h slim bundles.
# Keywords: bitcoin-trading, cursor_trade_history, sync, slim, automation

from __future__ import annotations

import argparse
import json
import subprocess
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "trades_control.json",
    "trades_treatment.json",
)

OPTIONAL_FILES = (
    "all_trades_bundle.json",
    "pnl_snapshot.json",
)

TIMESTAMP_CANDIDATES = (
    "timestamp",
    "ts",
    "time",
    "created_at",
    "updated_at",
    "entry_time",
    "exit_time",
    "opened_at",
    "closed_at",
    "event_time",
    "signal_time",
)


@dataclass
class FilterResult:
    kept: list[dict[str, Any]]
    dropped_no_timestamp: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync cursor trade history JSONs and build latest 24h slim files."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("/root/projects/bitcoin-trading/exports/cursor_trade_history"),
        help="Source directory containing trade history export files.",
    )
    parser.add_argument(
        "--dest-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "exports" / "cursor_trade_history",
        help="Destination directory to write synced and 24h slim files.",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Latest window in hours to keep (default: 24).",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Optional JSONL log path. Defaults to <dest-dir>/sync_latest_24h.log.jsonl.",
    )
    parser.add_argument(
        "--run-promotion-gate",
        action="store_true",
        help="Run strategy promotion gate evaluation after sync succeeds.",
    )
    parser.add_argument(
        "--promotion-gate-script",
        type=Path,
        default=Path(__file__).resolve().parent / "evaluate_trade_strategy_promotion_gate_v1.py",
        help="Promotion gate evaluation script path.",
    )
    return parser.parse_args()


def _parse_timestamp(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        # Heuristic: values > 1e12 are likely milliseconds.
        seconds = float(raw) / 1000.0 if float(raw) > 1_000_000_000_000 else float(raw)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (ValueError, OSError):
            return None
    if not isinstance(raw, str):
        return None

    value = raw.strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _extract_trade_time(trade: dict[str, Any]) -> datetime | None:
    for key in TIMESTAMP_CANDIDATES:
        if key in trade:
            parsed = _parse_timestamp(trade.get(key))
            if parsed is not None:
                return parsed.astimezone(timezone.utc)
    return None


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid json: {path} ({exc})") from exc


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sync_files(source_dir: Path, dest_dir: Path) -> tuple[list[str], list[str]]:
    copied: list[str] = []
    missing_optional: list[str] = []
    for name in REQUIRED_FILES:
        src = source_dir / name
        dst = dest_dir / name
        if not src.exists():
            raise RuntimeError(f"source file not found: {src}")
        # If source/destination are effectively same file, skip copy.
        if src.resolve() == dst.resolve():
            continue
        shutil.copy2(src, dst)
        copied.append(name)
    for name in OPTIONAL_FILES:
        src = source_dir / name
        dst = dest_dir / name
        if not src.exists():
            missing_optional.append(name)
            continue
        if src.resolve() == dst.resolve():
            continue
        shutil.copy2(src, dst)
        copied.append(name)
    return copied, missing_optional


def _filter_latest(trades: Any, start_utc: datetime) -> FilterResult:
    if not isinstance(trades, list):
        raise RuntimeError("trade file must be a JSON array.")
    kept: list[dict[str, Any]] = []
    dropped_no_timestamp = 0

    for item in trades:
        if not isinstance(item, dict):
            continue
        trade_time = _extract_trade_time(item)
        if trade_time is None:
            dropped_no_timestamp += 1
            continue
        if trade_time >= start_utc:
            kept.append(item)

    return FilterResult(kept=kept, dropped_no_timestamp=dropped_no_timestamp)


def _append_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _run_promotion_gate(script_path: Path, dest_dir: Path, log_file: Path) -> dict[str, Any]:
    if not script_path.exists():
        raise RuntimeError(f"promotion gate script not found: {script_path}")

    output_file = dest_dir / "strategy_promotion_gate_latest.json"
    shadow_file = dest_dir / "trades_treatment_v2_shadow.json"
    cmd = [
        sys.executable,
        str(script_path),
        "--control-file",
        str(dest_dir / "trades_control.json"),
        "--treatment-file",
        str(dest_dir / "trades_treatment.json"),
        "--shadow-file",
        str(shadow_file),
        "--output-file",
        str(output_file),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    status = "ok" if result.returncode == 0 else "error"
    _append_log(
        log_file,
        {
            "event": "strategy_promotion_gate_after_sync",
            "status": status,
            "script_path": str(script_path),
            "output_file": str(output_file),
            "return_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        },
    )
    if result.returncode != 0:
        raise RuntimeError(
            "promotion gate evaluation failed: "
            f"code={result.returncode} stderr={result.stderr.strip()}"
        )
    return {"output_file": str(output_file), "shadow_file": str(shadow_file)}


def main() -> int:
    args = _parse_args()
    source_dir = args.source_dir
    dest_dir = args.dest_dir
    log_file = args.log_file or (dest_dir / "sync_latest_24h.log.jsonl")
    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(hours=args.hours)

    if not source_dir.exists():
        print(f"[ERROR] source directory not found: {source_dir}", file=sys.stderr)
        return 2

    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        copied_files, missing_optional_files = _sync_files(source_dir=source_dir, dest_dir=dest_dir)

        control_raw = _read_json(dest_dir / "trades_control.json")
        treatment_raw = _read_json(dest_dir / "trades_treatment.json")
        snapshot_raw: dict[str, Any]
        snapshot_path = dest_dir / "pnl_snapshot.json"
        if snapshot_path.exists():
            loaded_snapshot = _read_json(snapshot_path)
            snapshot_raw = loaded_snapshot if isinstance(loaded_snapshot, dict) else {"raw": loaded_snapshot}
        else:
            snapshot_raw = {}

        control = _filter_latest(control_raw, start_utc=start_utc)
        treatment = _filter_latest(treatment_raw, start_utc=start_utc)

        all_latest = {
            "schema": "cursor_trade_history_latest_window_v1",
            "generated_at_utc": now_utc.isoformat(),
            "window_hours": args.hours,
            "window_start_utc": start_utc.isoformat(),
            "window_end_utc": now_utc.isoformat(),
            "counts": {
                "total": len(control.kept) + len(treatment.kept),
                "control": len(control.kept),
                "treatment": len(treatment.kept),
                "dropped_no_timestamp": control.dropped_no_timestamp + treatment.dropped_no_timestamp,
            },
            "control_id": "control",
            "treatment_id": "btc_prophecy_treatment_v1",
            "snapshot": snapshot_raw,
            "control": control.kept,
            "treatment": treatment.kept,
        }

        _write_json(dest_dir / "trades_control_latest_24h.json", control.kept)
        _write_json(dest_dir / "trades_treatment_latest_24h.json", treatment.kept)
        _write_json(dest_dir / "all_trades_latest_24h.json", all_latest)
        # SSOT pointer filename for downstream automations and dashboards.
        _write_json(dest_dir / "cursor_trade_history_latest_24h.json", all_latest)

        log_row = {
            "event": "sync_cursor_trade_history_latest_window",
            "status": "ok",
            "generated_at_utc": now_utc.isoformat(),
            "source_dir": str(source_dir),
            "dest_dir": str(dest_dir),
            "copied_files": copied_files,
            "missing_optional_files": missing_optional_files,
            "counts": all_latest["counts"],
            "window_hours": args.hours,
            "ssot_latest_file": str(dest_dir / "cursor_trade_history_latest_24h.json"),
        }
        _append_log(log_file, log_row)

        promotion_info: dict[str, Any] | None = None
        if args.run_promotion_gate:
            promotion_info = _run_promotion_gate(
                script_path=args.promotion_gate_script,
                dest_dir=dest_dir,
                log_file=log_file,
            )

        print("[OK] sync + latest window generation complete")
        print(f"source: {source_dir}")
        print(f"dest:   {dest_dir}")
        print(
            "counts: "
            f"control={len(control.kept)} "
            f"treatment={len(treatment.kept)} "
            f"total={all_latest['counts']['total']}"
        )
        if promotion_info is not None:
            print("[OK] promotion gate evaluated")
            print(f"gate_output: {promotion_info['output_file']}")
        return 0
    except RuntimeError as exc:
        _append_log(
            log_file,
            {
                "event": "sync_cursor_trade_history_latest_window",
                "status": "error",
                "generated_at_utc": now_utc.isoformat(),
                "source_dir": str(source_dir),
                "dest_dir": str(dest_dir),
                "error": str(exc),
                "window_hours": args.hours,
            },
        )
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
