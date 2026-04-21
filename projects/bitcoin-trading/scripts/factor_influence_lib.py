#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.6, L:0.9, K:0.7, M:0.85}
# Balance: 92
# Purpose: Shared factor influence log parsing and metrics for reporting scripts.
# Keywords: bitcoin-trading, factor-influence, logs

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


LINE_PATTERNS: dict[str, str] = {
    "signals": r"\b신호:\s*(BUY|SELL|HOLD)\b|\bsignal=(BUY|SELL|HOLD)\b|\b매매 신호\b",
    "trade_done": r"\btrade_done\b|거래(?:\s*실행|\s*완료)|주문\s*(?:성공|완료)|체결",
    "low_conf": r"\blow_conf(?:idence)?\b|low_confidence_hold|신뢰도\s*부족",
    "phase_pass": r"\bphase_pass\b|phase\s*pass|위상.*(?:통과|pass)",
    "sbsc_pass": r"\bsbsc_pass\b|sbsc.*(?:통과|pass)",
    "news_gdelt_fail": r"\bnews_gdelt_fail\b|gdelt.*(?:fail|실패)",
    "news_gdelt_fallback": r"\bnews_gdelt_fallback\b|gdelt.*fallback",
    "engine_fallback_ma": r"\bengine_fallback_ma\b|engine.*fallback.*ma",
    "vector_missing": r"\bvector_missing\b|vector.*(?:missing|없음|누락)",
    "global_liq_missing": r"\bglobal_liq_missing\b|global.*liq.*(?:missing|없음|누락)",
}

TS_RE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)

# Extract optional reason / token after keyword (best-effort for log lines).
_REASON_AFTER = re.compile(
    r"(?:vector_missing|engine_fallback_ma)"
    r'(?:[=:]\s*|"\s*:\s*"?|\'\s*:\s*\'?)'
    r"([^\s,}\]]{1,64})",
    re.IGNORECASE,
)
_JSON_STRING_VALUE = re.compile(
    r'"(?:vector_missing|engine_fallback_ma|fallback_reason|vector_reason)"\s*:\s*"([^"]{1,128})"',
    re.IGNORECASE,
)


@dataclass
class CountResult:
    counts: dict[str, int]
    total_lines: int
    matched_lines: int


def read_lines(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        return fh.read().splitlines()


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def compile_patterns() -> dict[str, re.Pattern[str]]:
    return {key: re.compile(pattern, re.IGNORECASE) for key, pattern in LINE_PATTERNS.items()}


def count_lines(lines: list[str], compiled: dict[str, re.Pattern[str]]) -> CountResult:
    counts = {key: 0 for key in LINE_PATTERNS}
    matched_lines = 0

    for line in lines:
        line_matched = False
        for key, pattern in compiled.items():
            if pattern.search(line):
                counts[key] += 1
                line_matched = True
        if line_matched:
            matched_lines += 1

    return CountResult(counts=counts, total_lines=len(lines), matched_lines=matched_lines)


def parse_line_ts(line: str) -> datetime | None:
    match = TS_RE.search(line)
    if not match:
        return None
    raw = match.group("ts").replace(",", ".")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    if re.search(r"[+-]\d{4}$", raw):
        raw = raw[:-5] + raw[-5:-2] + ":" + raw[-2:]
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def filter_by_hours(lines: list[str], window_start_utc: datetime) -> list[str]:
    kept: list[str] = []
    for line in lines:
        ts = parse_line_ts(line)
        if ts is None:
            continue
        if ts.astimezone(timezone.utc) >= window_start_utc:
            kept.append(line)
    return kept


def build_metrics(counts: dict[str, int]) -> dict[str, Any]:
    signals = counts["signals"]
    trade_done = counts["trade_done"]
    vector_missing = counts["vector_missing"]
    engine_fallback = counts["engine_fallback_ma"]
    low_conf = counts["low_conf"]
    phase_pass = counts["phase_pass"]
    sbsc_pass = counts["sbsc_pass"]
    gdelt_fail = counts["news_gdelt_fail"]
    gdelt_fallback = counts["news_gdelt_fallback"]
    global_liq_missing = counts["global_liq_missing"]
    gdelt_combined = gdelt_fail + gdelt_fallback

    return {
        "trade_done_per_signals": safe_ratio(trade_done, signals),
        "low_conf_per_signals": safe_ratio(low_conf, signals),
        "phase_pass_per_signals": safe_ratio(phase_pass, signals),
        "sbsc_pass_per_signals": safe_ratio(sbsc_pass, signals),
        "news_gdelt_combined_per_signals": safe_ratio(gdelt_combined, signals),
        "engine_fallback_ma_per_signals": safe_ratio(engine_fallback, signals),
        "vector_missing_per_signals": safe_ratio(vector_missing, signals),
        "global_liq_missing_per_signals": safe_ratio(global_liq_missing, signals),
        "global_liq_missing_per_trade_done": safe_ratio(global_liq_missing, trade_done),
        # Alias keys for dashboards / cron consumers (capped — tag lines can exceed signal lines)
        # Uncapped duplicates for alerting (can exceed 1.0 when tag lines > signal lines).
        "trade_done_rate_uncapped": safe_ratio(trade_done, signals),
        "vector_missing_rate_uncapped": safe_ratio(vector_missing, signals),
        "engine_fallback_ma_rate_uncapped": safe_ratio(engine_fallback, signals),
        "trade_done_rate": min(1.0, safe_ratio(trade_done, signals)),
        "vector_missing_rate": min(1.0, safe_ratio(vector_missing, signals)),
        "engine_fallback_ma_rate": min(1.0, safe_ratio(engine_fallback, signals)),
    }


def _normalize_bucket(raw: str) -> str:
    t = raw.strip()
    if not t:
        return "unspecified"
    if len(t) > 48:
        return t[:45] + "..."
    return t


def _extract_reason_token(line: str) -> str | None:
    jm = _JSON_STRING_VALUE.search(line)
    if jm:
        return _normalize_bucket(jm.group(1))
    rm = _REASON_AFTER.search(line)
    if rm:
        return _normalize_bucket(rm.group(1))
    try:
        if "{" in line and "}" in line:
            start = line.index("{")
            blob = line[start : line.rindex("}") + 1]
            data = json.loads(blob)
            if isinstance(data, dict):
                for k in ("vector_missing", "engine_fallback_ma", "fallback_reason", "vector_reason"):
                    v = data.get(k)
                    if isinstance(v, str) and v.strip():
                        return _normalize_bucket(v)
                    if isinstance(v, bool):
                        return str(v).lower()
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def breakdown_keyword(lines: list[str], keyword_pattern: re.Pattern[str], limit_samples: int = 5) -> dict[str, Any]:
    buckets: dict[str, int] = {}
    samples: list[str] = []

    for line in lines:
        if not keyword_pattern.search(line):
            continue
        token = _extract_reason_token(line) or "unspecified"
        buckets[token] = buckets.get(token, 0) + 1
        if len(samples) < limit_samples:
            tail = line.strip()
            if len(tail) > 240:
                tail = tail[:237] + "..."
            samples.append(tail)

    top = sorted(buckets.items(), key=lambda x: (-x[1], x[0]))[:12]
    return {
        "by_reason_token": dict(top),
        "total_tagged_lines": sum(buckets.values()),
        "sample_lines": samples,
    }


def compute_snapshot(
    log_file: Path,
    recent_lines: int,
    window_hours: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, int], dict[str, int]]:
    """Returns (latest_payload_flat_compat, recent_metrics, hour_metrics, recent_counts, hour_counts)."""
    now_utc = datetime.now(timezone.utc)
    if not log_file.exists():
        raise FileNotFoundError(str(log_file))

    lines = read_lines(log_file)
    recent_only = lines[-recent_lines:] if recent_lines > 0 else lines
    window_start = now_utc - timedelta(hours=window_hours)
    by_hour = filter_by_hours(lines, window_start)
    compiled = compile_patterns()

    recent_result = count_lines(recent_only, compiled)
    hour_result = count_lines(by_hour, compiled)

    vm_pat = compiled["vector_missing"]
    ef_pat = compiled["engine_fallback_ma"]

    primary_metrics = build_metrics(recent_result.counts)

    payload = {
        "schema": "factor_influence_report_v1",
        "exported_at": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_utc": now_utc.isoformat(),
        "source": {
            "log_file": str(log_file),
            "recent_lines": recent_lines,
            "window_hours": window_hours,
        },
        "rates_primary_scope": "recent_lines",
        "trade_done_rate": primary_metrics["trade_done_rate"],
        "vector_missing_rate": primary_metrics["vector_missing_rate"],
        "engine_fallback_ma_rate": primary_metrics["engine_fallback_ma_rate"],
        "trade_done_rate_uncapped": primary_metrics["trade_done_rate_uncapped"],
        "vector_missing_rate_uncapped": primary_metrics["vector_missing_rate_uncapped"],
        "engine_fallback_ma_rate_uncapped": primary_metrics["engine_fallback_ma_rate_uncapped"],
        "recent_lines": {
            "scope_total_lines": recent_result.total_lines,
            "matched_lines": recent_result.matched_lines,
            "counts": recent_result.counts,
            "metrics": build_metrics(recent_result.counts),
            "breakdown": {
                "vector_missing": breakdown_keyword(recent_only, vm_pat),
                "engine_fallback_ma": breakdown_keyword(recent_only, ef_pat),
            },
        },
        "window_24h": {
            "scope_total_lines": hour_result.total_lines,
            "matched_lines": hour_result.matched_lines,
            "counts": hour_result.counts,
            "metrics": build_metrics(hour_result.counts),
            "breakdown": {
                "vector_missing": breakdown_keyword(by_hour, vm_pat),
                "engine_fallback_ma": breakdown_keyword(by_hour, ef_pat),
            },
        },
        "delta_recent_minus_24h": {
            key: recent_result.counts[key] - hour_result.counts[key] for key in LINE_PATTERNS
        },
    }

    return (
        payload,
        build_metrics(recent_result.counts),
        build_metrics(hour_result.counts),
        recent_result.counts,
        hour_result.counts,
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
