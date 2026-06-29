"""Shared helpers for Field×Logos overlay prophecy B-track lane ([HYPO], NON_GATING)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIELD_SNAPSHOT = ROOT / "reports/field_regime_observational_snapshot_v1_latest.json"
DEFAULT_LOGOS_RESONANCE = ROOT / "docs/final/artifacts/logos_regime_resonance_shadow_signal_latest.json"
DEFAULT_HOLDOUT = ROOT / "docs/final/fixtures/field_logos_overlay_prophecy_holdout_v1.json"
DEFAULT_OVERLAY_OUT = ROOT / "docs/final/artifacts/field_logos_overlay_prophecy_v1_latest.json"
SCHEMA = "field_logos_overlay_prophecy_v1"
VERSION = "1.0.0"


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def load_holdout_items(path: Path) -> list[dict[str, Any]]:
    doc = read_json(path)
    if not doc:
        return []
    items = doc.get("items") or []
    return [it for it in items if isinstance(it, dict) and it.get("query_ko")]


def pick_regime_resonance_row(
    shadow: dict[str, Any] | None,
    primary_regime: str | None,
) -> tuple[dict[str, Any] | None, str | None, float | None]:
    if not shadow:
        return None, None, None
    rows = shadow.get("rows") if isinstance(shadow.get("rows"), list) else []
    if primary_regime:
        for row in rows:
            if isinstance(row, dict) and str(row.get("regime") or "") == primary_regime:
                cos = row.get("top_hit_cosine_to_regime")
                return row, primary_regime, float(cos) if cos is not None else None
    summary = shadow.get("summary") if isinstance(shadow.get("summary"), dict) else {}
    best = summary.get("best_regime")
    if best:
        for row in rows:
            if isinstance(row, dict) and str(row.get("regime") or "") == str(best):
                cos = row.get("top_hit_cosine_to_regime")
                return row, str(best), float(cos) if cos is not None else None
    if rows and isinstance(rows[0], dict):
        row = rows[0]
        cos = row.get("top_hit_cosine_to_regime")
        return row, str(row.get("regime") or ""), float(cos) if cos is not None else None
    return None, None, None


def fused_confidence(
    *,
    overlay_weight: float,
    router_top_score: int,
    resonance_cosine: float | None,
    theme_match_threshold: float,
) -> float:
    logos_part = min(1.0, max(0.0, router_top_score / 7.0))
    field_part = float(resonance_cosine or 0.0)
    raw = overlay_weight * logos_part + (1.0 - overlay_weight) * field_part
    if logos_part < theme_match_threshold and router_top_score < 3:
        raw *= 0.85
    return round(min(1.0, max(0.0, raw)), 4)


def router_bridge_artifacts(router: dict[str, Any] | None) -> list[str]:
    if not router:
        return []
    out: list[str] = []
    for path in router.get("paths") or []:
        if isinstance(path, dict):
            art = str(path.get("bridge_artifact") or "")
            if art and art not in out:
                out.append(art)
    return out


def router_top_match_score(router: dict[str, Any] | None) -> int:
    if not router:
        return 0
    scores = [
        int(p.get("match_score") or 0)
        for p in (router.get("paths") or [])
        if isinstance(p, dict)
    ]
    return max(scores) if scores else 0
