#!/usr/bin/env python3
"""[HYPO] RQ-032 — 인류 역사→era 전용 체인 (KOSPI 제거, research_only, NON_GATING).

Measures history→era alignment and quad-only regime tag observability.
Does NOT use KOSPI OHLCV, daily direction HR, or mutate ops / Track A.

Pillars:
  A) logos era blind eval — gold_tags (upper bound) + text_blind tier_v2 (MS/public cite)
  B) regime_map primary via quad uft_v2 only (no OHLCV year-end proxy)
  C) gold fixture + chronology coverage + general prophecy Brier pointer
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/rq032_logos_history_era_chain_v1_latest.json"
DEFAULT_POINTER = ROOT / "reports/rq032_logos_history_era_research_v1_latest.json"
SCHEMA = "rq032_logos_history_era_chain_v1"

DEFAULT_REGIME_MAP = ROOT / "data/regimes/regime_map.json"
DEFAULT_QUAD = ROOT / "data/quad_fusion_training/quad_fusion_result_20260308_230751.json"
DEFAULT_CHRONOLOGY = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_ERA_GOLD_TAGS = ROOT / "reports/logos_chronology_era_blind_eval_v1_latest.json"
DEFAULT_ERA_TEXT_BLIND = (
    ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_tier_v2_v1_latest.json"
)
DEFAULT_BRIER = ROOT / "docs/final/artifacts/general_prophecy_brier_eval_latest.json"

EVAL_SCRIPT = ROOT / "scripts/eval_logos_chronology_era_blind_v1.py"
PY = sys.executable


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _quad_year_vectors(quad_json: Path) -> dict[int, dict[str, float]]:
    quad = _load_json(quad_json) or {}
    out: dict[int, dict[str, float]] = {}
    for row in quad.get("uft_v2_timeline") or []:
        yr = int(row.get("year", -1))
        u4 = row.get("unified_4d_vector") or {}
        if yr < 0 or not u4:
            continue
        out[yr] = {k: float(u4[k]) for k in ("S", "L", "K", "M") if k in u4}
    return out


def _primary_regime_for_year(
    year: int,
    *,
    year_vecs: dict[int, dict[str, float]],
    regime_map: Path,
) -> dict[str, Any]:
    u4 = year_vecs.get(year) or year_vecs.get(year - 1)
    if not u4:
        return {"year": year, "primary_regime_id": None, "top_cosine": None, "vector_source": "missing_quad"}
    from scripts.build_field_regime_per_date_attachment_hypo_v1 import _rank_primary  # noqa: WPS433

    ranked = _rank_primary(
        u4,
        regime_map=regime_map,
        exclude_regime_ids={"unknown"},
        vector_source=f"quad_year_flat_{year}",
    )
    return {"year": year, **ranked}


def _macro_landmarks(gold: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in gold.get("events") or []:
        if not isinstance(ev, dict):
            continue
        if str(ev.get("tier") or "") != "macro_landmark":
            continue
        out.append(ev)
    return sorted(out, key=lambda e: str(e.get("as_of_date") or ""))


def _summarize_era_eval(doc: dict[str, Any] | None, *, label: str) -> dict[str, Any]:
    if not doc:
        return {"label": label, "status": "missing", "path_expected": True}
    summary = doc.get("summary") or {}
    governance = doc.get("governance") or {}
    return {
        "label": label,
        "status": doc.get("status"),
        "schema": doc.get("schema"),
        "generated_at_utc": doc.get("generated_at_utc"),
        "tag_mode": summary.get("tag_mode") or (doc.get("inputs") or {}).get("tag_mode"),
        "n_non_synthetic": summary.get("n_non_synthetic"),
        "hit_at_1_strict": summary.get("hit_at_1_strict"),
        "hit_at_1_relaxed": summary.get("hit_at_1_relaxed"),
        "hit_at_3": summary.get("hit_at_3"),
        "locked_eval_hit_at_1_strict": summary.get("locked_eval_hit_at_1_strict"),
        "macro_landmark_hit_at_1_strict": summary.get("macro_landmark_hit_at_1_strict"),
        "narrative_hit_at_1_strict": summary.get("narrative_hit_at_1_strict"),
        "governance_status": governance.get("status"),
        "governance_interpretation_ko": governance.get("interpretation_ko"),
        "known_limitations": doc.get("known_limitations") or [],
    }


def _pillar_a_era_blind(
    *,
    gold_tags_eval: dict[str, Any] | None,
    text_blind_eval: dict[str, Any] | None,
) -> dict[str, Any]:
    gold = _summarize_era_eval(gold_tags_eval, label="gold_tags_upper_bound")
    blind = _summarize_era_eval(text_blind_eval, label="text_blind_tier_v2_ms_public")
    return {
        "axis": "history_headline_to_biblical_era",
        "kospi_removed": True,
        "does_not_measure_price_direction": True,
        "gold_tags_eval": gold,
        "text_blind_eval": blind,
        "ms_public_headline_metric": {
            "cite": "text_blind_tier_v2 locked_eval hit@1_strict",
            "value": blind.get("locked_eval_hit_at_1_strict"),
            "do_not_cite": "gold_tags hit@1_strict (operator tag upper bound)",
            "gold_tags_upper_bound": gold.get("hit_at_1_strict"),
        },
        "interpretation_ko": (
            "[HYPO] 인류·매크로 사건 headline → Logos 연대기 era blind ranking. "
            "gold_tags=운영자 태그 상한; 대외·MS는 text_blind ~4–9%만. NON_GATING · Track A 무관."
        ),
    }


def _pillar_b_quad_regime_only(
    *,
    gold: dict[str, Any],
    year_vecs: dict[int, dict[str, float]],
    regime_map: Path,
) -> dict[str, Any]:
    events = _macro_landmarks(gold)
    rows: list[dict[str, Any]] = []
    strict_hits = quad_covered = 0
    n = 0
    quad_years = sorted(year_vecs)
    for ev in events:
        as_of = str(ev.get("as_of_date") or "")[:10]
        if len(as_of) < 4:
            continue
        yr = int(as_of[:4])
        primary = _primary_regime_for_year(yr, year_vecs=year_vecs, regime_map=regime_map)
        has_quad = yr in year_vecs or (yr - 1) in year_vecs
        pid = primary.get("primary_regime_id")
        tags = [str(t).strip().lower() for t in (ev.get("inferred_regime_tags") or []) if str(t).strip()]
        strict = bool(pid and tags and pid in tags)
        if has_quad and primary.get("vector_source", "").startswith("quad"):
            quad_covered += 1
            if strict:
                strict_hits += 1
        n += 1
        rows.append(
            {
                "event_id": ev.get("event_id"),
                "as_of_date": as_of,
                "inferred_regime_tags": tags,
                "primary_regime_id": pid if has_quad else None,
                "quad_year_available": has_quad,
                "strict_regime_tag_match": strict if has_quad else None,
                "gold_era_id": ev.get("gold_era_id"),
            }
        )
    return {
        "n_macro_landmarks": n,
        "quad_timeline_year_min": quad_years[0] if quad_years else None,
        "quad_timeline_year_max": quad_years[-1] if quad_years else None,
        "quad_coverage_rate": round(quad_covered / n, 6) if n else None,
        "strict_primary_in_inferred_tags_rate_quad_covered": round(strict_hits / quad_covered, 6)
        if quad_covered
        else None,
        "ohlcv_year_proxy_used": False,
        "kospi_removed": True,
        "interpretation_ko": (
            "[HYPO] quad uft_v2만으로 regime_map 1차 vs gold inferred_regime_tags. "
            "KOSPI OHLCV proxy 없음 — RQ-031 Pillar A의 ohlcv 보조 제거."
        ),
        "rows": rows,
    }


def _pillar_c_fixture_chronology(
    *,
    gold: dict[str, Any],
    chronology: dict[str, Any] | None,
    brier: dict[str, Any] | None,
) -> dict[str, Any]:
    events = [ev for ev in (gold.get("events") or []) if isinstance(ev, dict)]
    tier_counts = Counter(str(ev.get("tier") or "unknown") for ev in events)
    partition_counts = Counter(str(ev.get("partition") or "unknown") for ev in events)
    era_ids = {str(ev.get("gold_era_id") or "") for ev in events if ev.get("gold_era_id")}
    ch_eras = chronology.get("eras") or [] if chronology else []
    bridges = chronology.get("modern_bridges") or [] if chronology else []
    brier_summary: dict[str, Any] = {"status": "missing"}
    if brier:
        brier_summary = {
            "status": brier.get("status") or "ok",
            "mean_brier": (brier.get("summary") or {}).get("mean_brier_score"),
            "n_forecasts": (brier.get("summary") or {}).get("n_forecasts"),
            "note": "general prophecy axis — separate from era blind eval",
        }
    return {
        "gold_fixture": {
            "n_events": len(events),
            "n_macro_landmark": tier_counts.get("macro_landmark", 0),
            "n_biblical_narrative": tier_counts.get("biblical_narrative", 0),
            "partition_counts": dict(partition_counts),
            "unique_gold_era_ids": sorted(era_ids),
        },
        "chronology_ssot": {
            "n_eras": len(ch_eras),
            "n_modern_bridges": len(bridges),
            "schema": chronology.get("schema") if chronology else None,
        },
        "general_prophecy_brier_pointer": brier_summary,
    }


def _synthesis(
    pillar_a: dict[str, Any],
    pillar_b: dict[str, Any],
    pillar_c: dict[str, Any],
) -> dict[str, Any]:
    gold_hit = (pillar_a.get("gold_tags_eval") or {}).get("hit_at_1_strict")
    locked = (pillar_a.get("text_blind_eval") or {}).get("locked_eval_hit_at_1_strict")
    blind_hit = (pillar_a.get("text_blind_eval") or {}).get("hit_at_1_strict")
    quad_cov = pillar_b.get("quad_coverage_rate")
    strict_quad = pillar_b.get("strict_primary_in_inferred_tags_rate_quad_covered")
    findings: list[str] = []
    if gold_hit is not None:
        findings.append(f"Pillar A gold_tags hit@1 strict = {gold_hit:.1%} (upper bound — not for MS/public).")
    if blind_hit is not None:
        findings.append(f"Pillar A text_blind hit@1 strict = {blind_hit:.1%}; locked_eval = {locked:.1%} (MS cite).")
    if quad_cov is not None:
        findings.append(
            f"Pillar B quad-only regime coverage = {quad_cov:.1%} "
            f"(years {pillar_b.get('quad_timeline_year_min')}–{pillar_b.get('quad_timeline_year_max')})."
        )
    if strict_quad is not None:
        findings.append(f"Pillar B quad-covered strict regime∈tags = {strict_quad:.1%}.")
    findings.append(
        f"Pillar C gold n={((pillar_c.get('gold_fixture') or {}).get('n_events'))} · "
        f"chronology eras={((pillar_c.get('chronology_ssot') or {}).get('n_eras'))}."
    )
    return {
        "findings": findings,
        "auto_promote_ready": False,
        "track_a_mutated": False,
        "successor_of_rq031": "RQ-032 removes KOSPI structural windows and OHLCV regime proxy; history→era only.",
        "deliberate_separation_from_rq025_030b": (
            "RQ-025..030b = KOSPI daily directional HR vs train-majority 63.2%. "
            "RQ-032 = era alignment + quad regime observability — no comparable win/loss score."
        ),
        "readout_ko": [
            "인류·매크로 역사 흐름→Logos era 정렬은 KOSPI 일봉 예측과 다른 축.",
            "대외·MS: text_blind locked_eval만; gold_tags 70%대는 상한·NON_GATING.",
            "Track A·ops score·실매매 트리거 변경 없음.",
        ],
    }


def _run_eval_mode(
    *,
    tag_mode: str,
    report_json: Path,
    output_json: Path,
    boost_policy: str,
    modern_boost: float,
) -> tuple[int, Path]:
    report_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        PY,
        str(EVAL_SCRIPT),
        "--tag-mode",
        tag_mode,
        "--boost-policy",
        boost_policy,
        "--modern-boost",
        str(modern_boost),
        "--gold-json",
        str(DEFAULT_GOLD),
        "--chronology-json",
        str(DEFAULT_CHRONOLOGY),
        "--report-json",
        str(report_json),
        "--output-json",
        str(output_json),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
    return proc.returncode, report_json


def build_report(
    *,
    regime_map: Path,
    quad_json: Path,
    gold_json: Path,
    chronology_json: Path,
    era_gold_tags_json: Path,
    era_text_blind_json: Path,
    brier_json: Path,
) -> dict[str, Any]:
    gold = _load_json(gold_json)
    if not gold:
        raise FileNotFoundError(gold_json)
    year_vecs = _quad_year_vectors(quad_json)
    if not year_vecs:
        raise FileNotFoundError(f"missing quad timeline: {quad_json}")
    if not regime_map.is_file():
        raise FileNotFoundError(regime_map)

    pillar_a = _pillar_a_era_blind(
        gold_tags_eval=_load_json(era_gold_tags_json),
        text_blind_eval=_load_json(era_text_blind_json),
    )
    pillar_b = _pillar_b_quad_regime_only(gold=gold, year_vecs=year_vecs, regime_map=regime_map)
    pillar_c = _pillar_c_fixture_chronology(
        gold=gold,
        chronology=_load_json(chronology_json),
        brier=_load_json(brier_json),
    )
    synthesis = _synthesis(pillar_a, pillar_b, pillar_c)

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "hypothesis_tag": "[HYPO]",
        "boundary_ack": True,
        "research_only": True,
        "non_gating": True,
        "track_a_status": "blocked",
        "auto_promote_ready": False,
        "kospi_removed": True,
        "purpose_ko": "인류 역사→era 전용 — era blind + quad regime + fixture (KOSPI·일봉 HR 없음)",
        "inputs": {
            "regime_map": str(regime_map),
            "quad_json": str(quad_json),
            "chronology_json": str(chronology_json),
            "gold_json": str(gold_json),
            "era_gold_tags_json": str(era_gold_tags_json),
            "era_text_blind_json": str(era_text_blind_json),
            "brier_json": str(brier_json),
        },
        "pillar_a_era_blind_eval": pillar_a,
        "pillar_b_quad_regime_only": pillar_b,
        "pillar_c_fixture_chronology": pillar_c,
        "synthesis": synthesis,
        "not_measured": [
            "kospi_daily_directional_hit_rate",
            "kospi_structural_vol_windows",
            "ohlcv_year_end_regime_proxy",
            "wf_train_majority_63.2_beat",
            "live_trading_trigger",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--regime-map", type=Path, default=DEFAULT_REGIME_MAP)
    ap.add_argument("--quad-json", type=Path, default=DEFAULT_QUAD)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--era-gold-tags-json", type=Path, default=DEFAULT_ERA_GOLD_TAGS)
    ap.add_argument("--era-text-blind-json", type=Path, default=DEFAULT_ERA_TEXT_BLIND)
    ap.add_argument("--brier-json", type=Path, default=DEFAULT_BRIER)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pointer-json", type=Path, default=DEFAULT_POINTER)
    ap.add_argument(
        "--run-eval",
        action="store_true",
        help="Refresh era blind eval (gold_tags + text_blind) into rq032 report paths before aggregate",
    )
    ap.add_argument("--modern-boost", type=float, default=0.08)
    ap.add_argument("--boost-policy", default="tier_v2_locked_eval")
    args = ap.parse_args()

    era_gold = args.era_gold_tags_json if args.era_gold_tags_json.is_absolute() else ROOT / args.era_gold_tags_json
    era_blind = (
        args.era_text_blind_json if args.era_text_blind_json.is_absolute() else ROOT / args.era_text_blind_json
    )

    if args.run_eval:
        rq032_gold_rep = ROOT / "reports/rq032_era_blind_gold_tags_v1_latest.json"
        rq032_gold_art = ROOT / "docs/final/artifacts/rq032_era_blind_gold_tags_v1_latest.json"
        rq032_blind_rep = ROOT / "reports/rq032_era_blind_text_blind_v1_latest.json"
        rq032_blind_art = ROOT / "docs/final/artifacts/rq032_era_blind_text_blind_v1_latest.json"
        rc1, _ = _run_eval_mode(
            tag_mode="gold_tags",
            report_json=rq032_gold_rep,
            output_json=rq032_gold_art,
            boost_policy=args.boost_policy,
            modern_boost=args.modern_boost,
        )
        rc2, _ = _run_eval_mode(
            tag_mode="text_blind",
            report_json=rq032_blind_rep,
            output_json=rq032_blind_art,
            boost_policy=args.boost_policy,
            modern_boost=args.modern_boost,
        )
        if rc1 != 0 or rc2 != 0:
            return 2
        era_gold = rq032_gold_rep
        era_blind = rq032_blind_rep

    try:
        report = build_report(
            regime_map=args.regime_map if args.regime_map.is_absolute() else ROOT / args.regime_map,
            quad_json=args.quad_json if args.quad_json.is_absolute() else ROOT / args.quad_json,
            gold_json=args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json,
            chronology_json=(
                args.chronology_json if args.chronology_json.is_absolute() else ROOT / args.chronology_json
            ),
            era_gold_tags_json=era_gold,
            era_text_blind_json=era_blind,
            brier_json=args.brier_json if args.brier_json.is_absolute() else ROOT / args.brier_json,
        )
    except FileNotFoundError as exc:
        print(f"MISSING: {exc}", file=sys.stderr)
        return 2

    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    ptr = args.pointer_json if args.pointer_json.is_absolute() else ROOT / args.pointer_json
    out.parent.mkdir(parents=True, exist_ok=True)
    ptr.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ms_metric = report["pillar_a_era_blind_eval"].get("ms_public_headline_metric") or {}
    pointer = {
        "schema": "rq032_logos_history_era_research_v1",
        "generated_at_utc": report["generated_at_utc"],
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "kospi_removed": True,
        "artifact": str(out),
        "gold_tags_hit_at_1_strict": (report["pillar_a_era_blind_eval"].get("gold_tags_eval") or {}).get(
            "hit_at_1_strict"
        ),
        "text_blind_hit_at_1_strict": (report["pillar_a_era_blind_eval"].get("text_blind_eval") or {}).get(
            "hit_at_1_strict"
        ),
        "text_blind_locked_eval_hit_at_1_strict": ms_metric.get("value"),
        "quad_coverage_rate": report["pillar_b_quad_regime_only"].get("quad_coverage_rate"),
        "quad_strict_regime_tag_rate": report["pillar_b_quad_regime_only"].get(
            "strict_primary_in_inferred_tags_rate_quad_covered"
        ),
        "synthesis": report["synthesis"],
    }
    ptr.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "pointer": str(ptr)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
