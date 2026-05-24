"""Per-eval_date multilens loop (myeongni/sasang) from calendar JSONL — no paid API.

Mirrors scoring heuristics in run_lens_myeongni.py / run_lens_sasang.py v0.2.0 for each
eval_date with causal as-of (rows with calendar day <= eval_date only).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SASANG_JSONL = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
DEFAULT_MYEONGNI_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"
DEFAULT_LOGOS_LENS = ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"

MYEONGNI_MAPPING_TO_SCORE: dict[str, float] = {
    "bull": 0.55,
    "bear": -0.55,
    "sideways": 0.0,
}
SASANG_MAPPING_TO_SCORE: dict[str, float] = MYEONGNI_MAPPING_TO_SCORE.copy()
STATE_PRIOR_SCORE: dict[int, float] = {
    6: -0.12,
    7: -0.22,
    8: -0.08,
    9: 0.18,
    10: -0.16,
    11: -0.06,
    12: 0.20,
    13: -0.10,
    14: 0.14,
    15: 0.24,
    16: -0.18,
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            rows.append(o)
    return rows


def rows_by_calendar_day(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_day: dict[str, dict[str, Any]] = {}
    for r in rows:
        ts = str(r.get("ts_utc") or "").strip()
        if len(ts) >= 10 and ts[4] == "-" and ts[7] == "-":
            by_day[ts[:10]] = r
    return by_day


def causal_rows_through(by_day: dict[str, dict[str, Any]], eval_date: str) -> list[dict[str, Any]]:
    ed = eval_date[:10]
    days = sorted(d for d in by_day if d <= ed)
    return [by_day[d] for d in days]


def row_asof(by_day: dict[str, dict[str, Any]], eval_date: str) -> tuple[str | None, dict[str, Any] | None]:
    ed = eval_date[:10]
    eligible = [d for d in by_day if d <= ed]
    if not eligible:
        return None, None
    chosen = max(eligible)
    return chosen, by_day[chosen]


def dir_to_sign(direction: str) -> int:
    d = (direction or "").strip().lower()
    if d == "bull":
        return 1
    if d == "bear":
        return -1
    return 0


def sign_to_dir(sign: int) -> str:
    if sign > 0:
        return "bull"
    if sign < 0:
        return "bear"
    return "neutral"


def logos_global(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"direction_score": None, "sign": 0, "data_quality": "missing", "non_gating": True}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"direction_score": None, "sign": 0, "data_quality": "parse_error", "non_gating": True}
    scores = raw.get("scores") if isinstance(raw.get("scores"), dict) else {}
    ds = scores.get("direction_score")
    try:
        v = float(ds)
    except (TypeError, ValueError):
        v = 0.0
    sign = 1 if v > 0 else (-1 if v < 0 else 0)
    return {
        "direction_score": round(v, 6),
        "confidence": scores.get("confidence"),
        "sign": sign,
        "data_quality": "independent_lens_global",
        "non_gating": True,
    }


def _mapping_score(row: dict[str, Any]) -> float:
    mt = str(row.get("mapping_target") or "").strip().lower()
    return MYEONGNI_MAPPING_TO_SCORE.get(mt, 0.0)


def _state_id(row: dict[str, Any]) -> int | None:
    raw = row.get("state_id")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw == int(raw):
        return int(raw)
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return None


def _calibrate_confidence(*, consistency: float, contradiction: float, rows_seen: int) -> float:
    reliability = min(1.0, max(0.2, rows_seen / 30.0))
    raw = consistency * max(0.0, 1.0 - contradiction)
    calibrated = 0.5 + (raw - 0.5) * reliability
    return max(0.05, min(0.95, calibrated))


def score_myeongni_at_date(
    history: list[dict[str, Any]],
    *,
    eval_date: str,
    matched_day: str | None,
    momentum_window: int = 5,
) -> dict[str, Any]:
    if not history:
        return {
            "direction_score": 0.0,
            "confidence": 0.5,
            "mapping_target": None,
            "matched_calendar_day": matched_day,
            "data_quality": "missing",
        }
    row = history[-1]
    tail = history[-max(1, momentum_window) :]
    momentum = sum(_mapping_score(r) for r in tail) / float(len(tail))
    mt = str(row.get("mapping_target") or "").strip().lower()
    direct = MYEONGNI_MAPPING_TO_SCORE.get(mt, 0.0)
    sid = _state_id(row)
    prior = STATE_PRIOR_SCORE.get(sid or -1, 0.0)
    direction = (0.55 * direct) + (0.35 * momentum) + (0.10 * prior)
    if abs(direction) < 0.04:
        direction = 0.0 if abs(prior) < 0.12 else 0.08 * (1.0 if prior > 0 else -1.0)
    direction = max(-1.0, min(1.0, direction))
    cr = row.get("consistency_rate")
    sr = row.get("self_contradiction_rate")
    consistency = float(cr) if isinstance(cr, (int, float)) else 0.5
    contradiction = float(sr) if isinstance(sr, (int, float)) else 0.0
    conf = _calibrate_confidence(
        consistency=consistency, contradiction=contradiction, rows_seen=len(history)
    )
    stub = bool(row.get("stub"))
    return {
        "direction_score": round(direction, 6),
        "confidence": round(conf, 6),
        "mapping_target": mt or None,
        "state_id": sid,
        "matched_calendar_day": matched_day,
        "eval_date": eval_date[:10],
        "causal_rows_seen": len(history),
        "data_quality": "calendar_stub" if stub else "calendar_jsonl",
        "engine_mirror": "run_lens_myeongni_v0.2.0_per_date",
    }


def _sasang_confidence(row: dict[str, Any]) -> float:
    mr = row.get("machine_readables")
    if not isinstance(mr, dict):
        return 0.5
    heat = mr.get("heat_proxy")
    cold = mr.get("cold_proxy")
    vol = mr.get("volatility_rarefaction_proxy")
    if not all(isinstance(x, (int, float)) for x in (heat, cold, vol)):
        return 0.5
    imbalance = abs(float(heat) - float(cold))
    conf = 0.45 + (0.35 * float(vol)) + (0.55 * imbalance)
    return max(0.0, min(1.0, conf))


def _sasang_direction(row: dict[str, Any], mt: str) -> float:
    base = SASANG_MAPPING_TO_SCORE.get(mt, 0.0)
    if mt != "sideways":
        return base
    mr = row.get("machine_readables")
    if not isinstance(mr, dict):
        return 0.0
    heat = mr.get("heat_proxy")
    cold = mr.get("cold_proxy")
    if not isinstance(heat, (int, float)) or not isinstance(cold, (int, float)):
        return 0.0
    delta = float(heat) - float(cold)
    if abs(delta) < 0.02:
        return 0.0
    return max(-0.18, min(0.18, delta))


def score_sasang_at_date(row: dict[str, Any] | None, *, matched_day: str | None, eval_date: str) -> dict[str, Any]:
    if row is None:
        return {
            "direction_score": 0.0,
            "confidence": 0.5,
            "mapping_target": None,
            "matched_calendar_day": matched_day,
            "data_quality": "missing",
        }
    mt = str(row.get("mapping_target") or "").strip().lower()
    direction = _sasang_direction(row, mt)
    stub = bool(row.get("stub"))
    return {
        "direction_score": round(direction, 6),
        "confidence": round(_sasang_confidence(row), 6),
        "mapping_target": mt or None,
        "regime_hypothesis": row.get("regime_hypothesis"),
        "matched_calendar_day": matched_day,
        "eval_date": eval_date[:10],
        "data_quality": "calendar_stub" if stub else "calendar_jsonl",
        "engine_mirror": "run_lens_sasang_v0.2.0_per_date",
    }


def lens_majority_sign(myeongni: dict[str, Any], sasang: dict[str, Any], *, include_logos: bool = False, logos: dict[str, Any] | None = None) -> int:
    signs = []
    for block in (myeongni, sasang):
        ds = block.get("direction_score")
        if isinstance(ds, (int, float)):
            if ds > 0:
                signs.append(1)
            elif ds < 0:
                signs.append(-1)
    if include_logos and logos:
        signs.append(int(logos.get("sign") or 0))
    non_zero = [s for s in signs if s != 0]
    if not non_zero:
        return 0
    total = sum(non_zero)
    if total > 0:
        return 1
    if total < 0:
        return -1
    return 0


def build_per_date_row(
    score_row: dict[str, Any],
    *,
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    logos_block: dict[str, Any],
    momentum_window: int = 5,
) -> dict[str, Any]:
    ed = str(score_row.get("eval_date") or "")[:10]
    inst = str(score_row.get("instrument") or "").strip().lower()
    my_hist = causal_rows_through(myeongni_by_day, ed)
    my_day, my_asof = row_asof(myeongni_by_day, ed)
    sa_day, sa_asof = row_asof(sasang_by_day, ed)
    my = score_myeongni_at_date(my_hist, eval_date=ed, matched_day=my_day, momentum_window=momentum_window)
    sa = score_sasang_at_date(sa_asof, matched_day=sa_day, eval_date=ed)
    majority = lens_majority_sign(my, sa, include_logos=False)
    price_sign = dir_to_sign(str(score_row.get("predicted_direction") or "neutral"))
    return {
        "eval_date": ed,
        "instrument": inst,
        "predicted_direction": score_row.get("predicted_direction"),
        "actual_direction": score_row.get("actual_direction"),
        "daily_return": score_row.get("daily_return"),
        "price_predicted_sign": price_sign,
        "lenses": {
            "logos": logos_block,
            "myeongni": my,
            "sasang": sa,
        },
        "lens_majority_sign": majority,
        "lens_majority_direction": sign_to_dir(majority),
        "lens_disagrees_with_price_pred": (
            price_sign != 0 and majority != 0 and price_sign != majority
        ),
        "loop_mode": "causal_calendar_jsonl_per_date_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "direction_promotion_allowed": False,
        "role_ko": "size/confidence 보조·관측; Track A·prod 방향 합선 금지.",
    }


def build_document(
    score_rows: list[dict[str, Any]],
    *,
    instrument: str = "btc",
    myeongni_jsonl: Path = DEFAULT_MYEONGNI_JSONL,
    sasang_jsonl: Path = DEFAULT_SASANG_JSONL,
    logos_lens: Path = DEFAULT_LOGOS_LENS,
    momentum_window: int = 5,
) -> dict[str, Any]:
    my_by = rows_by_calendar_day(read_jsonl(myeongni_jsonl))
    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))
    logos_block = logos_global(logos_lens)
    out_rows: list[dict[str, Any]] = []
    for r in score_rows:
        if not isinstance(r, dict):
            continue
        inst = str(r.get("instrument") or "").strip().lower()
        if instrument != "all" and inst != instrument:
            continue
        out_rows.append(
            build_per_date_row(
                r,
                myeongni_by_day=my_by,
                sasang_by_day=sa_by,
                logos_block=logos_block,
                momentum_window=momentum_window,
            )
        )
    out_rows.sort(key=lambda x: (x.get("eval_date") or "", x.get("instrument") or ""))
    return {
        "schema": "btrack_multilens_per_date_lens_v1",
        "version": "1.0.0",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "instrument_filter": instrument,
        "n_rows": len(out_rows),
        "inputs": {
            "myeongni_jsonl": str(myeongni_jsonl).replace("\\", "/"),
            "sasang_jsonl": str(sasang_jsonl).replace("\\", "/"),
            "logos_lens_json": str(logos_lens).replace("\\", "/"),
        },
        "loop_contract": {
            "causal": "calendar day <= eval_date",
            "myeongni_momentum_window": momentum_window,
            "logos": "global_snapshot_non_gating",
            "paid_api": False,
        },
        "rows": out_rows,
    }
