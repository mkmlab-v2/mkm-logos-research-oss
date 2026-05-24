#!/usr/bin/env python3
"""B-track: match macro observation packet to Logos chronology eras [HYPO].

Outputs resonance scores + disagreement_index. Does NOT write Track A, live trading, or prophecy score.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHRONO = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_MACRO = ROOT / "docs/final/artifacts/macro_independent_lens_latest.json"
DEFAULT_NEWS = ROOT / "docs/final/artifacts/news_independent_lens_latest.json"
DEFAULT_REGIME_MAP = ROOT / "data/regimes/regime_map.json"
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/chronology_regime_match_v1_latest.json"

# Sub-era overlays (not separate chronology v2 eras yet)
SUB_ERAS: dict[str, dict[str, Any]] = {
    "joseph_storehouse_hypo": {
        "parent_era_id": "patriarch_covenant_arc",
        "label_ko": "요셉 · 비축·기근 대비 [HYPO]",
        "theme_tags": [
            "storehouse",
            "famine",
            "grain_reserve",
            "central_planning",
            "surplus",
            "buffer",
            "hoarding",
            "fiscal_reserve",
        ],
    },
    "nehemiah_rebuild_hypo": {
        "parent_era_id": "exile_and_return",
        "label_ko": "느헤미야 · 성벽·인프라 재건 [HYPO]",
        "theme_tags": [
            "rebuild",
            "wall",
            "infrastructure",
            "governance_restore",
            "restoration",
            "supply_chain",
            "reshoring",
            "regulation",
        ],
    },
}

OBSERVATION_KEYWORDS = frozenset(
    """
    infrastructure rebuild wall regulation reshoring supply chain fiscal reserve buffer
    hoarding surplus famine grain ai capex datacenter liquidity tightening crisis shock
    recovery return exile judgment covenant network expansion empire handoff babel
    fragmentation regulation split governance stabilization rally bear risk-off
    """.split()
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def _era_keywords(era: dict[str, Any]) -> set[str]:
    parts: list[str] = []
    for t in era.get("theme_tags") or []:
        if isinstance(t, str):
            parts.append(t)
    notes = era.get("notes_ko") or era.get("label_ko") or ""
    if isinstance(notes, str):
        parts.append(notes)
    for r in era.get("regime_tags_observational") or []:
        if isinstance(r, str):
            parts.append(r)
    return _tokens(" ".join(parts))


def _macro_observation_text(macro: dict[str, Any] | None, news: dict[str, Any] | None, packet: dict[str, Any] | None) -> str:
    if packet:
        chunks = []
        for k in ("headlines", "themes", "keywords", "summary_ko", "body"):
            v = packet.get(k)
            if isinstance(v, str):
                chunks.append(v)
            elif isinstance(v, list):
                chunks.extend(str(x) for x in v)
        if chunks:
            return " ".join(chunks)
    parts: list[str] = []
    if macro:
        parts.append(json.dumps(macro.get("scores") or {}, ensure_ascii=False))
        mo = macro.get("macro_stream_outputs") or {}
        parts.append(json.dumps(mo, ensure_ascii=False))
    if news:
        parts.append(json.dumps(news.get("scores") or {}, ensure_ascii=False))
    parts.append(" ".join(OBSERVATION_KEYWORDS))
    return " ".join(parts)


def _score_era(obs_tokens: set[str], era_kw: set[str]) -> float:
    if not era_kw:
        return 0.0
    inter = len(obs_tokens & era_kw)
    union = len(obs_tokens | era_kw) or 1
    return inter / union


def _disagreement_index(scores: list[float]) -> float:
    if not scores:
        return 1.0
    s = sorted(scores, reverse=True)
    top = s[0]
    second = s[1] if len(s) > 1 else 0.0
    total = sum(s) or 1e-9
    # High when top is not dominant: blend entropy proxy + margin
    margin = (top - second) / max(top, 1e-9)
    dominance = top / total
    return round(max(0.0, min(1.0, 1.0 - 0.5 * dominance - 0.5 * margin)), 6)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chronology regime match v1 (B-track [HYPO])")
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONO)
    ap.add_argument("--macro-json", type=Path, default=DEFAULT_MACRO)
    ap.add_argument("--news-json", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--macro-packet-json", type=Path, default=None, help="Optional SOAP-style macro packet")
    ap.add_argument("--regime-map-json", type=Path, default=DEFAULT_REGIME_MAP)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--include-sub-eras", action="store_true", default=True)
    args = ap.parse_args(argv)

    chrono_path = args.chronology_json if args.chronology_json.is_absolute() else ROOT / args.chronology_json
    chrono = _read_json(chrono_path)
    if not chrono or not isinstance(chrono.get("eras"), list):
        print(f"Missing or invalid chronology: {chrono_path}", file=sys.stderr)
        return 2

    macro = _read_json(args.macro_json if args.macro_json.is_absolute() else ROOT / args.macro_json)
    news = _read_json(args.news_json if args.news_json.is_absolute() else ROOT / args.news_json)
    packet = None
    if args.macro_packet_json:
        packet = _read_json(args.macro_packet_json if args.macro_packet_json.is_absolute() else ROOT / args.macro_packet_json)

    obs_text = _macro_observation_text(macro, news, packet)
    obs_tokens = _tokens(obs_text)

    candidates: list[dict[str, Any]] = []
    for era in chrono["eras"]:
        if not isinstance(era, dict):
            continue
        eid = str(era.get("era_id") or "")
        kw = _era_keywords(era)
        sc = _score_era(obs_tokens, kw)
        candidates.append(
            {
                "match_id": eid,
                "kind": "chronology_era",
                "label_ko": era.get("label_ko"),
                "resonance_score": round(sc, 6),
                "parent_era_id": None,
            }
        )

    if args.include_sub_eras:
        for sid, sub in SUB_ERAS.items():
            kw = _tokens(" ".join(sub.get("theme_tags") or []))
            sc = _score_era(obs_tokens, kw)
            candidates.append(
                {
                    "match_id": sid,
                    "kind": "sub_era_hypo",
                    "label_ko": sub.get("label_ko"),
                    "resonance_score": round(sc, 6),
                    "parent_era_id": sub.get("parent_era_id"),
                }
            )

    candidates.sort(key=lambda r: float(r["resonance_score"]), reverse=True)
    scores_only = [float(c["resonance_score"]) for c in candidates]
    disagreement = _disagreement_index(scores_only)
    top = candidates[0] if candidates else None

    regime_map_path = args.regime_map_json if args.regime_map_json.is_absolute() else ROOT / args.regime_map_json
    regime_primary: str | None = None
    rm = _read_json(regime_map_path)
    if rm and isinstance(rm.get("regimes"), dict) and rm["regimes"]:
        regime_primary = next(iter(rm["regimes"].keys()), None)

    doc: dict[str, Any] = {
        "schema": "chronology_regime_match_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "interpretation_class": "[HYPO]",
        "non_gating": True,
        "no_trading_signal": True,
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
            "overwrite_prophecy_score": False,
        },
        "inputs": {
            "chronology_json": str(chrono_path.resolve()),
            "macro_json": str((ROOT / args.macro_json).resolve()) if macro else None,
            "news_json": str((ROOT / args.news_json).resolve()) if news else None,
            "macro_packet_json": str(args.macro_packet_json) if packet else None,
            "regime_map_json": str(regime_map_path.resolve()) if rm else None,
        },
        "primary_regime_map_observational": regime_primary,
        "top_match": top,
        "runner_up": candidates[1] if len(candidates) > 1 else None,
        "disagreement_index": disagreement,
        "operator_hint_ko": (
            "disagreement_index 높으면 단일 연대기 단정 금지. "
            "1차 Field=regime_map 실물; 본 매칭=Logos 부록 [HYPO] only."
        ),
        "routing_hint": {
            "infrastructure_rebuild_axis": "nehemiah_rebuild_hypo / exile_and_return",
            "storehouse_famine_buffer_axis": "joseph_storehouse_hypo / patriarch_covenant_arc",
        },
        "ranked_matches": candidates[:15],
        "candidate_count": len(candidates),
    }

    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "wrote": str(out), "top_match_id": top.get("match_id") if top else None, "disagreement_index": disagreement}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
