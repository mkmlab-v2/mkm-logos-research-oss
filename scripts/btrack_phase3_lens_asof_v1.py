"""Per-eval_date lens as-of helpers for Phase 3 B-track (research_only)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SASANG_JSONL = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
DEFAULT_MYEONGNI_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"
DEFAULT_LOGOS_LENS = ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"


def dir_to_sign(direction: str) -> int:
    d = (direction or "").strip().lower()
    if d == "bull":
        return 1
    if d == "bear":
        return -1
    return 0


def jsonl_last_row_by_calendar_day(path: Path) -> dict[str, dict[str, Any]]:
    by_day: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return by_day
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(o, dict):
                continue
            ts = str(o.get("ts_utc") or "").strip()
            if len(ts) >= 10 and ts[4] == "-" and ts[7] == "-":
                by_day[ts[:10]] = o
    return by_day


def row_asof_calendar_day(
    by_day: dict[str, dict[str, Any]],
    eval_date: str,
) -> tuple[str | None, dict[str, Any] | None]:
    if not by_day or not eval_date or len(eval_date) < 10:
        return None, None
    d0 = eval_date[:10]
    eligible = [d for d in by_day if d <= d0]
    if not eligible:
        return None, None
    return max(eligible), by_day[max(eligible)]


def logos_sign_from_independent_lens(path: Path) -> tuple[int, str]:
    if not path.is_file():
        return 0, "missing"
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return 0, "parse_error"
    if not isinstance(raw, dict):
        return 0, "invalid"
    scores = raw.get("scores") if isinstance(raw.get("scores"), dict) else {}
    ds = scores.get("direction_score")
    try:
        v = float(ds)
    except (TypeError, ValueError):
        return 0, "independent_lens_global"
    if v > 0:
        return 1, "independent_lens_global"
    if v < 0:
        return -1, "independent_lens_global"
    return 0, "independent_lens_global"


def lens_row_for_eval_date(
    eval_date: str,
    *,
    logos_sign: int,
    logos_quality: str,
    sasang_by_day: dict[str, dict[str, Any]],
    myeongni_by_day: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ed = eval_date[:10]
    sa_day, sa_row = row_asof_calendar_day(sasang_by_day, ed)
    my_day, my_row = row_asof_calendar_day(myeongni_by_day, ed)
    sa_sign = dir_to_sign(str(sa_row.get("mapping_target") or "neutral")) if sa_row else 0
    my_sign = dir_to_sign(str(my_row.get("mapping_target") or "neutral")) if my_row else 0
    sa_stub = bool(sa_row.get("stub")) if sa_row else False
    my_stub = bool(my_row.get("stub")) if my_row else False
    non_zero = [s for s in (logos_sign, my_sign, sa_sign) if s != 0]
    majority = 0
    if non_zero:
        majority = 1 if sum(non_zero) > 0 else -1 if sum(non_zero) < 0 else 0
        if abs(sum(non_zero)) < len(non_zero):
            majority = 0
    return {
        "logos_sign": logos_sign,
        "logos_data_quality": logos_quality,
        "myeongni_sign": my_sign,
        "myeongni_matched_calendar_day": my_day,
        "myeongni_data_quality": "calendar_stub" if my_stub else ("calendar_jsonl" if my_row else "missing"),
        "sasang_sign": sa_sign,
        "sasang_matched_calendar_day": sa_day,
        "sasang_data_quality": "calendar_stub" if sa_stub else ("calendar_jsonl" if sa_row else "missing"),
        "non_neutral_lens_count": len(non_zero),
        "lens_majority_sign": majority,
        "logos_non_gating": True,
    }
