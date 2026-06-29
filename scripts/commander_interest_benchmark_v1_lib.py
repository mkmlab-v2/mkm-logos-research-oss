#!/usr/bin/env python3
"""Shared helpers for commander interest benchmark + AI-native briefing chain."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_CONFIG = ART / "commander_interest_benchmark_config_v1.default.json"
DEFAULT_LOG = ROOT / "reports" / "commander_interest_signal_log_v1.jsonl"
EXAMPLE_LOG = ART / "commander_interest_signal_log_v1.example.jsonl"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def ensure_signal_log(log_path: Path = DEFAULT_LOG, *, bootstrap_example: bool = False) -> Path:
    log_path = resolve_path(log_path)
    if log_path.is_file():
        return log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if bootstrap_example and EXAMPLE_LOG.is_file():
        shutil.copyfile(EXAMPLE_LOG, log_path)
    else:
        log_path.write_text("", encoding="utf-8")
    return log_path


def is_excluded_signal(row: dict[str, Any], config: dict[str, Any] | None) -> bool:
    cfg = config or {}
    url = str(row.get("url") or "")
    for pattern in cfg.get("exclude_url_patterns") or ["example.com"]:
        if pattern and pattern in url:
            return True
    note = str(row.get("note") or "")
    for marker in cfg.get("exclude_note_markers") or ["[HYPO] sample"]:
        if marker and marker in note:
            return True
    return False


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    cfg_path = resolve_path(path)
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Missing config: {cfg_path}")
    return load_json(cfg_path)


def load_signals(
    log_path: Path,
    *,
    start: datetime,
    end: datetime,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    log_path = resolve_path(log_path)
    if not log_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if is_excluded_signal(row, config):
            continue
        ts = parse_ts(row.get("observed_at_utc"))
        if ts is None or ts < start or ts > end:
            continue
        rows.append(row)
    return rows


def engagement_score(row: dict[str, Any], weights: dict[str, float]) -> float:
    explicit = row.get("engagement_score")
    if explicit is not None:
        try:
            return float(explicit)
        except (TypeError, ValueError):
            pass
    total = 0.0
    for key, weight in weights.items():
        try:
            total += float(row.get(key) or 0) * float(weight)
        except (TypeError, ValueError):
            continue
    return total


def topic_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for topic in config.get("topics") or []:
        tid = str(topic.get("id") or "").strip()
        if tid:
            out[tid] = topic
    return out


def window_bounds(window_days: int, *, end: datetime | None = None) -> tuple[datetime, datetime]:
    end_dt = end or utc_now()
    start_dt = end_dt - timedelta(days=int(window_days))
    return start_dt, end_dt
