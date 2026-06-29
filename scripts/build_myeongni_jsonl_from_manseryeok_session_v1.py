#!/usr/bin/env python3
"""Emit myeongni/sasang JSONL from PerfectManseryeok session wall-clock (B-track).

Per eval_date: session 四柱 at market open (default 09:00 Asia/Seoul) → quant profile →
mapping_target from session-only ten-god balance (same family as mkm_myeongni_math).

Not 擇日/日課; research_only. Separate output paths — do not overwrite v1_latest sidecar.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_btrack_session_instant_myeongni_panel_v1 import (  # noqa: E402
    SessionPanelParams,
    iter_session_rows,
)
from scripts.myeongni_lens_v1.mkm_myeongni_math import (  # noqa: E402
    STEM_META,
    _canonical_stem_char,
    _count_ten_gods,
    _extract_surface_stems,
    _first_char,
    compute_quant_profile_v0,
)

DEFAULT_MYEONGNI_OUT = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_SASANG_OUT = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_COMMANDER = ROOT / "docs/final/artifacts/commander_profile_v1.example.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _score_from_session_pillars(pillars: dict[str, str]) -> float:
    """Session-only direction proxy (no birth chart blend)."""
    adv = {"pillars": pillars, "sajeong_interpolation": {}, "school_signals": []}
    day_stem = _canonical_stem_char(_first_char(pillars.get("day")))
    if day_stem not in STEM_META:
        return 0.0
    surface = _extract_surface_stems(pillars)
    if not surface:
        return 0.0
    counts = _count_ten_gods(day_stem, surface)
    surface_total = max(1, len(surface))
    ten_god_balance = (counts["sik_sin"] + counts["sang_gwan"] - counts["pyeon_in"] - counts["jeong_in"]) / float(
        surface_total
    )
    mass = compute_quant_profile_v0(adv).get("five_element_mass_vector_v0") or {}
    if not isinstance(mass, dict):
        mass = {}
    wood = float(mass.get("목") or 0)
    fire = float(mass.get("화") or 0)
    earth = float(mass.get("토") or 0)
    metal = float(mass.get("금") or 0)
    water = float(mass.get("수") or 0)
    yang_elems = wood + fire
    yin_elems = metal + water
    elem_bias = (yang_elems - yin_elems) / max(1e-6, yang_elems + yin_elems + earth)
    return max(-1.0, min(1.0, 0.6 * ten_god_balance + 0.4 * elem_bias))


def _mapping_from_score(score: float, neutral_band: float) -> str:
    if score > neutral_band:
        return "bull"
    if score < -neutral_band:
        return "bear"
    return "sideways"


def _state_id_from_session_score(score: float) -> int:
    """Map session score to 6..16 band (B-track experiment compatibility)."""
    band = int(round((max(-1.0, min(1.0, score)) + 1.0) * 5.0))
    return 6 + max(0, min(10, band))


def build_myeongni_session_jsonl_rows(
    *,
    date_from: str,
    date_to: str,
    calendar_mode: str = "krx_weekdays",
    neutral_band: float = 0.06,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    d0 = date.fromisoformat(date_from)
    d1 = date.fromisoformat(date_to)
    params = SessionPanelParams(
        date_from=d0,
        date_to=d1,
        iana_tz="Asia/Seoul",
        hour=9,
        minute=0,
        second=0,
        calendar_mode=calendar_mode,
        dst_fold=1,
    )

    my_lines: list[dict[str, Any]] = []
    sa_lines: list[dict[str, Any]] = []
    for row in iter_session_rows(params):
        ed = str(row.get("session_local_date") or "")[:10]
        pillars = {
            "year": row.get("year_pillar"),
            "month": row.get("month_pillar"),
            "day": row.get("day_pillar"),
            "hour": row.get("hour_pillar"),
        }
        score = _score_from_session_pillars({k: str(v or "") for k, v in pillars.items()})
        mt = _mapping_from_score(score, neutral_band)
        heat = min(0.62, max(0.38, 0.5 + score * 0.12))
        cold = 1.0 - heat
        sid = _state_id_from_session_score(score)
        my_lines.append(
            {
                "ts_utc": f"{ed}T13:00:00Z",
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "stub": False,
                "source": "manseryeok_session_v1",
                "source_provenance": "manseryeok_session_per_date_v1",
                "underlying_may_be_calendar_stub": False,
                "eval_date": ed,
                "state_id": sid,
                "mapping_target": mt,
                "session_direction_score": round(score, 6),
                "pillars_session": pillars,
                "consistency_rate": round(min(0.9, 0.55 + abs(score) * 0.35), 3),
                "self_contradiction_rate": round(max(0.03, 0.12 - abs(score) * 0.05), 3),
                "run_id": "manseryeok_session_30y_v1",
            }
        )
        sa_mt = mt if mt != "sideways" else ("bull" if score > 0 else "bear" if score < 0 else "sideways")
        sa_lines.append(
            {
                "ts_utc": f"{ed}T12:00:00+00:00",
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "stub": False,
                "source": "manseryeok_session_v1",
                "source_provenance": "manseryeok_session_per_date_v1",
                "underlying_may_be_calendar_stub": False,
                "eval_date": ed,
                "mapping_target": sa_mt,
                "regime_hypothesis": "phase_transition",
                "machine_readables": {
                    "heat_proxy": round(heat, 3),
                    "cold_proxy": round(cold, 3),
                    "session_direction_score": round(score, 6),
                },
            }
        )

    counts = {"bull": 0, "bear": 0, "sideways": 0}
    for x in my_lines:
        counts[str(x["mapping_target"])] = counts.get(str(x["mapping_target"]), 0) + 1

    meta = {
        "session_panel": {
            "date_from": date_from,
            "date_to": date_to,
            "calendar_mode": calendar_mode,
            "open_local": "09:00 Asia/Seoul",
        },
        "n_days": len(my_lines),
        "mapping_target_counts": counts,
        "neutral_band": neutral_band,
    }
    return my_lines, sa_lines, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="2014-09-17")
    ap.add_argument("--date-to", default="2026-06-04")
    ap.add_argument("--calendar-mode", default="all", choices=("all", "krx_weekdays"))
    ap.add_argument("--neutral-band", type=float, default=0.06)
    ap.add_argument("--myeongni-out", type=Path, default=DEFAULT_MYEONGNI_OUT)
    ap.add_argument("--sasang-out", type=Path, default=DEFAULT_SASANG_OUT)
    ap.add_argument("--commander-profile", type=Path, default=DEFAULT_COMMANDER)
    args = ap.parse_args()

    my_lines, sa_lines, panel_meta = build_myeongni_session_jsonl_rows(
        date_from=args.date_from,
        date_to=args.date_to,
        calendar_mode=args.calendar_mode,
        neutral_band=args.neutral_band,
    )

    args.myeongni_out.parent.mkdir(parents=True, exist_ok=True)
    args.sasang_out.parent.mkdir(parents=True, exist_ok=True)
    args.myeongni_out.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in my_lines) + "\n",
        encoding="utf-8",
    )
    args.sasang_out.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in sa_lines) + "\n",
        encoding="utf-8",
    )

    root_resolved = ROOT.resolve()
    meta = {
        "schema": "myeongni_jsonl_from_manseryeok_session_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "commander_profile_ref": str(args.commander_profile.resolve().relative_to(root_resolved)).replace("\\", "/"),
        **panel_meta,
        "myeongni_out": str(args.myeongni_out.resolve().relative_to(root_resolved)).replace("\\", "/"),
        "sasang_out": str(args.sasang_out.resolve().relative_to(root_resolved)).replace("\\", "/"),
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
