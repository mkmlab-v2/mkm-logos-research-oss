#!/usr/bin/env python3
"""[HYPO] Causal micro-oscillator tie-break helpers for per-date lens combo (B-track)."""

from __future__ import annotations

from typing import Any

MICRO_MODES = frozenset(
    {
        "off",
        "mom_ret1",
        "revert_ret1",
        "mom_ret3",
        "composite_ret1_ret3",
        "vol_gated_mom_ret1",
    }
)


def _feat_for_row(
    row: dict[str, Any],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
) -> dict[str, float]:
    inst = str(row.get("instrument") or "").strip().lower()
    ed = str(row.get("eval_date") or "").strip()[:10]
    if inst == "kospi":
        return dict(kf.get(ed) or {})
    return dict(bf.get(ed) or {})


def micro_oscillator_sign(
    feat: dict[str, float],
    mode: str,
    *,
    dz: float = 0.0,
    vol_ratio_min: float = 1.0,
) -> int:
    """Return +1 bull, -1 bear, 0 no micro signal."""
    m = str(mode or "off").strip().lower()
    if m in ("off", "", "none"):
        return 0
    # Use lagged 1d return (t-2→t-1) when present — ret_1 may include same-day close (leak).
    ret1 = float(feat.get("ret_1_lagged") if feat.get("ret_1_lagged") is not None else feat.get("ret_1") or 0.0)
    ret3 = float(feat.get("ret_3") or 0.0)
    vol3 = float(feat.get("vol_3") or 0.0)
    vol10 = float(feat.get("vol_10") or 0.0)

    def _sign_ret(x: float) -> int:
        if x >= dz:
            return 1
        if x <= -dz:
            return -1
        return 0

    if m == "mom_ret1":
        return _sign_ret(ret1)
    if m == "revert_ret1":
        s = _sign_ret(ret1)
        return -s if s else 0
    if m == "mom_ret3":
        return _sign_ret(ret3)
    if m == "composite_ret1_ret3":
        combo = _sign_ret(ret1) + _sign_ret(ret3)
        if combo > 0:
            return 1
        if combo < 0:
            return -1
        return 0
    if m == "vol_gated_mom_ret1":
        if vol10 <= 0.0 or vol3 < vol10 * float(vol_ratio_min):
            return 0
        return _sign_ret(ret1)
    raise ValueError(f"unsupported micro_oscillator mode: {mode}")


def combo_score_is_ambiguous(
    score: float,
    up_thr: float,
    down_thr: float,
    *,
    margin: float = 0.0,
) -> bool:
    """True when combo score is inside (down, up) or within margin of a threshold (weak conviction)."""
    s, u, d = float(score), float(up_thr), float(down_thr)
    m = max(0.0, float(margin or 0.0))
    if d < s < u:
        return True
    if m > 0.0:
        if s >= u and (s - u) <= m:
            return True
        if s <= d and (d - s) <= m:
            return True
    return False


def micro_trigger_allows_apply(
    trigger: str,
    *,
    base_pred: str,
    combo_score: float | None = None,
    up_thr: float | None = None,
    down_thr: float | None = None,
    ambiguous_margin: float = 0.0,
) -> bool:
    t = str(trigger or "neutral").strip().lower()
    pred = str(base_pred or "").strip().lower()
    if t == "all":
        return True
    if t == "neutral":
        return pred == "neutral"
    if t == "ambiguous":
        if combo_score is None or up_thr is None or down_thr is None:
            return pred == "neutral"
        return combo_score_is_ambiguous(
            combo_score,
            up_thr,
            down_thr,
            margin=ambiguous_margin,
        )
    raise ValueError(f"unsupported micro_oscillator trigger: {trigger}")


def apply_micro_tiebreak(
    base_pred: str,
    row: dict[str, Any],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    *,
    mode: str,
    dz: float = 0.0,
    only_neutral: bool = True,
    trigger: str | None = None,
    combo_score: float | None = None,
    up_thr: float | None = None,
    down_thr: float | None = None,
    ambiguous_margin: float = 0.0,
    vol_ratio_min: float = 1.0,
) -> tuple[str, bool]:
    """Apply micro layer on test rows only (caller responsibility). Returns (pred, micro_applied)."""
    pred = str(base_pred or "").strip().lower()
    m = str(mode or "off").strip().lower()
    if m in ("off", "", "none"):
        return pred, False
    eff_trigger = trigger if trigger is not None else ("neutral" if only_neutral else "all")
    if not micro_trigger_allows_apply(
        eff_trigger,
        base_pred=pred,
        combo_score=combo_score,
        up_thr=up_thr,
        down_thr=down_thr,
        ambiguous_margin=ambiguous_margin,
    ):
        return pred, False
    sig = micro_oscillator_sign(
        _feat_for_row(row, kf, bf),
        m,
        dz=float(dz),
        vol_ratio_min=float(vol_ratio_min),
    )
    if sig > 0:
        return "bull", True
    if sig < 0:
        return "bear", True
    return pred, False


def sign_to_direction(sig: int) -> str | None:
    if sig > 0:
        return "bull"
    if sig < 0:
        return "bear"
    return None
