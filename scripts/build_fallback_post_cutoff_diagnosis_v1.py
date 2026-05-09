#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVENT_LOG = ROOT / "reports" / "constitution" / "btrack_pilot" / "fallback_trigger_event_log_v1.jsonl"
PROFILE = ROOT / "docs" / "final" / "artifacts" / "fallback_trigger_threshold_profile_latest.json"
OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "fallback_post_cutoff_diagnosis_latest.json"
OUT_MD = ROOT / "docs" / "final" / "artifacts" / "fallback_post_cutoff_diagnosis_latest.md"
WINDOW_HOURS = 24


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(raw: Any) -> datetime | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if p <= 0:
        return float(sorted_vals[0])
    if p >= 100:
        return float(sorted_vals[-1])
    idx = (len(sorted_vals) - 1) * (p / 100.0)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    w = idx - lo
    return float(sorted_vals[lo] * (1.0 - w) + sorted_vals[hi] * w)


def main() -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=WINDOW_HOURS)
    baseline_raw = os.environ.get("FALLBACK_POST_CUTOFF_BASELINE_RESET_UTC", "").strip()
    baseline = _parse_dt(baseline_raw)
    if baseline is None and PROFILE.is_file():
        try:
            baseline = _parse_dt((json.loads(PROFILE.read_text(encoding="utf-8-sig"))).get("generated_at_utc"))
        except Exception:
            baseline = None
    effective_cutoff = max(cutoff, baseline) if baseline is not None else cutoff

    rows: list[dict[str, Any]] = []
    if EVENT_LOG.is_file():
        for line in EVENT_LOG.read_text(encoding="utf-8-sig").splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            ts = _parse_dt(obj.get("ts_utc"))
            if ts is None or ts < effective_cutoff:
                continue
            rows.append(obj)

    reasons = Counter()
    tiers = Counter()
    token_vals: list[float] = []
    token_rows = 0
    for r in rows:
        tiers[str(r.get("tier") or "unknown")] += 1
        rs = r.get("reasons")
        if isinstance(rs, list):
            for x in rs:
                reasons[str(x)] += 1
        tok = r.get("input_tokens")
        if isinstance(tok, (int, float)):
            token_rows += 1
            token_vals.append(float(tok))
    token_vals.sort()

    total = len(rows)
    triggered = sum(1 for r in rows if bool(r.get("triggered", False)))
    trigger_rate = (triggered / total) if total else 0.0

    sims: list[dict[str, Any]] = []
    if token_vals:
        for th in (12000, 14000, 16000):
            hit = sum(1 for v in token_vals if v > th)
            sims.append(
                {
                    "input_tokens_threshold": th,
                    "rows_over_threshold": hit,
                    "rate_over_threshold": round(hit / len(token_vals), 6),
                }
            )

    out = {
        "schema": "fallback_post_cutoff_diagnosis_v1",
        "generated_at_utc": _iso_now(),
        "window_hours": WINDOW_HOURS,
        "baseline_reset_utc": baseline.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(baseline, datetime) else None,
        "effective_cutoff_utc": effective_cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_event_log": str(EVENT_LOG.resolve()).replace("\\", "/"),
        "summary": {
            "rows_total": total,
            "triggered_count": triggered,
            "trigger_rate": round(trigger_rate, 6),
            "token_rows": token_rows,
            "token_coverage_rate": round((token_rows / total), 6) if total else 0.0,
        },
        "top_reasons": [{"reason": k, "count": v} for k, v in reasons.most_common(5)],
        "tier_distribution": dict(tiers),
        "token_distribution": {
            "p50": _percentile(token_vals, 50),
            "p90": _percentile(token_vals, 90),
            "p99": _percentile(token_vals, 99),
            "max": float(token_vals[-1]) if token_vals else None,
        },
        "threshold_simulation_input_tokens": sims,
        "note": (
            "input_tokens simulation is only meaningful when token coverage is high. "
            "If token_coverage_rate is low, update producers to append input_tokens in fallback events."
        ),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Fallback Post-Cutoff Diagnosis",
        "",
        f"- effective_cutoff_utc: `{out['effective_cutoff_utc']}`",
        f"- rows_total: `{out['summary']['rows_total']}`",
        f"- triggered_count: `{out['summary']['triggered_count']}`",
        f"- trigger_rate: `{out['summary']['trigger_rate']}`",
        f"- token_coverage_rate: `{out['summary']['token_coverage_rate']}`",
        "",
        "## Token Distribution",
        f"- p50: `{out['token_distribution']['p50']}`",
        f"- p90: `{out['token_distribution']['p90']}`",
        f"- p99: `{out['token_distribution']['p99']}`",
        f"- max: `{out['token_distribution']['max']}`",
    ]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
