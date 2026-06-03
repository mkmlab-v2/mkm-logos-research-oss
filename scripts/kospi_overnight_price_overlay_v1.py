"""KOSPI price-lens overnight overlay (US/Asia prior) — Phase B [HYPO]."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERNIGHT = ROOT / "docs/final/artifacts/global_market_overnight_signals_v1_latest.json"

US_IDS = frozenset({"dow", "nasdaq", "sp500", "nasdaq_yf", "ndx"})
ASIA_IDS = frozenset({"nikkei225", "hang_seng", "shanghai"})


def _truthy(name: str, default: bool = True) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _pct_to_score(change_pct: float) -> float:
    return _clamp(float(change_pct) / 1.2)


def _mean_scores(indices: list[dict[str, Any]], ids: frozenset[str]) -> float | None:
    vals: list[float] = []
    for row in indices:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id") or "").lower()
        if rid not in ids:
            continue
        try:
            vals.append(_pct_to_score(float(row.get("change_pct") or 0.0)))
        except (TypeError, ValueError):
            continue
    if not vals:
        return None
    return sum(vals) / len(vals)


def load_global_overnight(path: Path | None = None) -> dict[str, Any] | None:
    p = path or DEFAULT_OVERNIGHT
    if not p.is_file():
        return None
    doc = json.loads(p.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) and doc.get("schema") == "global_market_overnight_signals_v1" else None


def compute_overnight_price_scores(overnight_doc: dict[str, Any] | None) -> dict[str, Any]:
    if not overnight_doc:
        return {"present": False, "reason": "overnight_missing"}
    indices = overnight_doc.get("indices") if isinstance(overnight_doc.get("indices"), list) else []
    us = _mean_scores(indices, US_IDS)
    asia = _mean_scores(indices, ASIA_IDS)
    if us is None and asia is None:
        return {"present": False, "reason": "no_index_rows"}
    if us is None:
        blended = asia
    elif asia is None:
        blended = us
    else:
        blended = 0.75 * us + 0.25 * asia
    composite = str(overnight_doc.get("composite_tilt") or "")
    return {
        "present": True,
        "composite_tilt": composite,
        "us_overnight_score": us,
        "asia_overnight_score": asia,
        "blended_overnight_score": blended,
        "session_anchor_date": overnight_doc.get("session_anchor_date"),
    }


def apply_kospi_overnight_price_overlay(
    price_score: float,
    price_conf: float,
    price_meta: dict[str, Any],
    *,
    overnight_doc: dict[str, Any] | None = None,
    overnight_path: Path | None = None,
) -> tuple[float, float, dict[str, Any]]:
    """Blend domestic KOSPI momentum with global overnight prior for open-gap research lane."""
    meta = dict(price_meta or {})
    if not _truthy("MKM_KOSPI_OVERNIGHT_PRICE_OVERLAY", default=True):
        meta["kospi_overnight_overlay"] = {"applied": False, "reason": "env_disabled"}
        return price_score, price_conf, meta

    doc = overnight_doc if overnight_doc is not None else load_global_overnight(overnight_path)
    ovn = compute_overnight_price_scores(doc)
    if not ovn.get("present"):
        meta["kospi_overnight_overlay"] = {"applied": False, "reason": ovn.get("reason", "missing")}
        return price_score, price_conf, meta

    blended = float(ovn["blended_overnight_score"])
    composite = str(ovn.get("composite_tilt") or "")
    domestic_w = 0.35
    overnight_w = 0.65
    if composite == "risk_off_overnight":
        domestic_w, overnight_w = 0.28, 0.72
    elif composite == "risk_on_overnight":
        domestic_w, overnight_w = 0.42, 0.58

    new_score = domestic_w * float(price_score) + overnight_w * blended
    new_conf = min(1.0, max(float(price_conf), 0.35 + 0.25 * abs(blended)))

    meta["kospi_overnight_overlay"] = {
        "applied": True,
        "phase": "B",
        "research_only": True,
        "domestic_weight": domestic_w,
        "overnight_weight": overnight_w,
        "domestic_price_score": round(float(price_score), 6),
        "blended_overnight_score": round(blended, 6),
        "price_score_after_blend": round(new_score, 6),
        **{k: v for k, v in ovn.items() if k != "present"},
        "overnight_artifact": str((overnight_path or DEFAULT_OVERNIGHT).as_posix()),
    }
    return new_score, new_conf, meta
