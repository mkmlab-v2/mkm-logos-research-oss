#!/usr/bin/env python3
"""Aggregate Logos passive drift metrics with dual-cohort raw reporting + measurement loop.

  py scripts/build_logos_passive_drift_governance_v1.py

Outputs:
  docs/final/artifacts/logos_passive_drift_governance_v1_latest.json
  docs/final/artifacts/logos_passive_drift_governance_v1_latest.md
  reports/logos_passive_drift_governance_history.jsonl  (append one line)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "docs/final/artifacts/logos_passive_drift_governance_v1_latest.json"
OUT_MD = ROOT / "docs/final/artifacts/logos_passive_drift_governance_v1_latest.md"
HISTORY = ROOT / "reports/logos_passive_drift_governance_history.jsonl"
HOLDOUT = ROOT / "reports/logos_chronology_text_blind_v2_holdout_v1_latest.json"
OFF_AB = ROOT / "reports/logos_chronology_off_fixture_text_blind_v2_ab_v1_latest.json"
EN_V2 = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v2_en_headline_v1_latest.json"
LEXICON = ROOT / "reports/lexicon_lookup_smoke_v1_latest.json"
HORIZON = ROOT / "docs/final/artifacts/logos_macro_horizon_2030_scenario_v1_latest.json"
PRIOR = OUT_JSON


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pct(v: float | int | None) -> str:
    if v is None:
        return "—"
    return f"{100.0 * float(v):.1f}%"


def _cohort_dual_report(
    holdout: dict[str, Any] | None,
    off_ab: dict[str, Any] | None,
    en_v2: dict[str, Any] | None,
) -> dict[str, Any]:
    train: dict[str, Any] = {}
    if holdout:
        part = (holdout.get("by_partition") or {}).get("train_holdout") or {}
        v1 = (part.get("text_blind_v1_ms_baseline") or {}).get("hit_at_1_strict")
        v2 = (part.get("text_blind_v2_btrack_poc") or {}).get("hit_at_1_strict")
        train = {
            "cohort": "historical_fixture.train_holdout",
            "n": (part.get("text_blind_v1_ms_baseline") or {}).get("n"),
            "raw": {"v1_ms_baseline_strict": v1, "v2_btrack_strict": v2},
            "delta_v2_minus_v1": part.get("delta_v2_minus_v1"),
            "interpretation_ko": "OOS-style primary slice — 패시브 드리프트 SSOT",
        }

    off: dict[str, Any] = {}
    if off_ab:
        cmp_ = off_ab.get("compare") or {}
        off = {
            "cohort": "off_fixture_disjoint_from_historical_47",
            "n": ((off_ab.get("text_blind_v1_ms_baseline") or {}).get("summary") or {}).get("n_events"),
            "raw": {
                "v1_ms_baseline_strict": cmp_.get("all_events_hit_at_1_v1"),
                "v2_btrack_strict": cmp_.get("all_events_hit_at_1_v2"),
            },
            "delta_v2_minus_v1": cmp_.get("delta_v2_minus_v1"),
            "interpretation_ko": "v1=v2 동점이면 v2 무개선 parity — 85.1%와 혼동 금지",
        }

    en: dict[str, Any] = {}
    if en_v2:
        s = en_v2.get("summary") or {}
        en = {
            "cohort": "historical_47_en_headline_v2_only",
            "n": s.get("n_events"),
            "raw": {"v2_btrack_strict": s.get("hit_at_1_strict")},
            "interpretation_ko": "영어 헤드라인 단독 코호트 — holdout/off-fixture와 별도",
        }

    return {
        "train_holdout": train,
        "off_fixture_ab": off,
        "en_headline_v2": en,
        "guardrails_ko": [
            "85.1%는 EN 47건 v2 단독 hit — off-fixture parity(68.75%/68.75%)와 다른 지표",
            "MS/본선 baseline=text_blind v1 (~6.4%) — v2 auto-apply 영구 금지",
            "Final Action·실매매 Key 주입 금지 ([NON_GATING])",
        ],
    }


def _drift_vs_prior(current: dict[str, Any], prior: dict[str, Any] | None) -> dict[str, Any]:
    if not prior:
        return {"status": "baseline", "note_ko": "선행 스냅샷 없음 — 이번 run이 baseline"}
    cur = current.get("cohorts") or {}
    old = prior.get("cohorts") or {}
    deltas: dict[str, Any] = {}

    for key in ("train_holdout", "off_fixture_ab"):
        c_raw = ((cur.get(key) or {}).get("raw") or {}).get("v2_btrack_strict")
        o_raw = ((old.get(key) or {}).get("raw") or {}).get("v2_btrack_strict")
        if c_raw is not None and o_raw is not None:
            deltas[key] = round(float(c_raw) - float(o_raw), 6)

    flags: list[str] = []
    th = deltas.get("train_holdout")
    if th is not None and abs(th) >= 0.05:
        flags.append("train_holdout_v2_shift_ge_5pp")
    off = deltas.get("off_fixture_ab")
    if off is not None and abs(off) >= 0.05:
        flags.append("off_fixture_v2_shift_ge_5pp")

    return {
        "status": "compared",
        "prior_generated_at_utc": prior.get("generated_at_utc"),
        "delta_v2_strict_minus_prior": deltas,
        "drift_flags": flags,
        "action_ko": "플래그 시 eval fixture/chronology SHA만 재검 — Track A 승격 금지",
    }


def _metacognition_loop(cohorts: dict[str, Any], drift: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "logos_measurement_loop_v1",
        "purpose_ko": "운영 메타인지 — 코호트·지표 혼선 방지·드리프트 관측 (자율 Track A 승격 아님)",
        "learned_guardrails": cohorts.get("guardrails_ko") or [],
        "drift_status": drift.get("status"),
        "drift_flags": drift.get("drift_flags") or [],
        "self_evolution_boundary_ko": (
            "본 루프는 디스크 아티팩트·exit code·human gate만 갱신한다. "
            "모델·baseline·MS 본문·실매매 파라미터 자동 rewrite 금지."
        ),
        "next_operator_actions": [
            "주 1회: py scripts/run_logos_passive_drift_governance_chain_v1.py --fast",
            "드리프트 플래그 시: fixture/chronology 입력 SHA 확인 후 --full 재실행",
            "Track C viz: docs/final/artifacts/logos_trackc_topology_radar_anchor_v1_latest.json 참조",
        ],
    }


def build_payload(*, lexicon: dict[str, Any] | None = None) -> dict[str, Any]:
    holdout = _load(HOLDOUT)
    off_ab = _load(OFF_AB)
    en_v2 = _load(EN_V2)
    lex = lexicon if lexicon is not None else _load(LEXICON)
    horizon = _load(HORIZON)

    cohorts = _cohort_dual_report(holdout, off_ab, en_v2)
    prior = _load(PRIOR) if PRIOR.is_file() else None
    drift = _drift_vs_prior({"cohorts": cohorts}, prior)

    btc_stress: dict[str, Any] = {"base": 0.27, "stress": 0.73}
    if horizon:
        weights = horizon.get("scenario_probability_weights") or {}
        by_axis = weights.get("by_axis") or {}
        btc = by_axis.get("btc") or {}
        if btc.get("base") is not None and btc.get("stress") is not None:
            btc_stress = {"base": btc["base"], "stress": btc["stress"]}

    return {
        "schema": "logos_passive_drift_governance_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_trading_signal": True,
            "auto_apply_text_blind_v2": False,
            "ms_baseline_unchanged": "text_blind_tier_v1_only",
        },
        "inputs": {
            "holdout_json": HOLDOUT.relative_to(ROOT).as_posix(),
            "off_fixture_ab_json": OFF_AB.relative_to(ROOT).as_posix(),
            "en_headline_v2_json": EN_V2.relative_to(ROOT).as_posix(),
            "lexicon_smoke_json": LEXICON.relative_to(ROOT).as_posix(),
            "horizon_scenario_json": HORIZON.relative_to(ROOT).as_posix(),
        },
        "cohorts": cohorts,
        "lexicon_rail": {
            "ok": (lex or {}).get("ok"),
            "lexicon_path": (lex or {}).get("lexicon_path"),
            "production_ssot_path": (lex or {}).get("production_ssot_path"),
            "row_counts": (lex or {}).get("row_counts"),
            "pointer_matches_resolved": ((lex or {}).get("alignment") or {}).get("pointer_matches_resolved"),
            "clinical_cds_merge_forbidden": True,
            "note_ko": "공용 compression lookup rail only — 임상 Logos 합선 금지",
        },
        "track_c_anchor": {
            "horizon_end_year": (horizon or {}).get("scope", {}).get("horizon_end_year"),
            "btc_base_stress": btc_stress or {"base": 0.27, "stress": 0.73},
            "topology_radar_anchor": "docs/final/artifacts/logos_trackc_topology_radar_anchor_v1_latest.json",
        },
        "drift": drift,
        "measurement_loop": _metacognition_loop(cohorts, drift),
        "reproduce": "py scripts/build_logos_passive_drift_governance_v1.py",
    }


def _render_md(doc: dict[str, Any]) -> str:
    c = doc.get("cohorts") or {}
    th = c.get("train_holdout") or {}
    off = c.get("off_fixture_ab") or {}
    en = c.get("en_headline_v2") or {}
    th_raw = th.get("raw") or {}
    off_raw = off.get("raw") or {}
    en_raw = en.get("raw") or {}
    drift = doc.get("drift") or {}
    lex = doc.get("lexicon_rail") or {}
    loop = doc.get("measurement_loop") or {}

    lines = [
        "# Logos passive drift governance",
        "",
        f"**Generated:** `{doc.get('generated_at_utc')}` · `[HYPO]` · `[NON_GATING]`",
        "",
        "## Dual-cohort raw (do not collapse)",
        "",
        "| Cohort | n | v1 strict | v2 strict | Δ v2−v1 |",
        "|--------|---|-----------|-----------|---------|",
        f"| train_holdout | {th.get('n', '—')} | {_pct(th_raw.get('v1_ms_baseline_strict'))} | "
        f"{_pct(th_raw.get('v2_btrack_strict'))} | {th.get('delta_v2_minus_v1', '—')} |",
        f"| off_fixture AB | {off.get('n', '—')} | {_pct(off_raw.get('v1_ms_baseline_strict'))} | "
        f"{_pct(off_raw.get('v2_btrack_strict'))} | {off.get('delta_v2_minus_v1', '—')} |",
        f"| EN headline v2 only | {en.get('n', '—')} | — | {_pct(en_raw.get('v2_btrack_strict'))} | — |",
        "",
        "## Lexicon rail",
        "",
        f"- resolved: `{lex.get('lexicon_path')}` · hits ok={lex.get('ok')}",
        f"- production SSOT: `{lex.get('production_ssot_path')}` · pointer match={lex.get('pointer_matches_resolved')}",
        f"- row counts: `{json.dumps(lex.get('row_counts') or {}, ensure_ascii=False)}`",
        "",
        "## Drift vs prior",
        "",
        f"- status: `{drift.get('status')}`",
        f"- flags: `{drift.get('drift_flags') or []}`",
        f"- deltas: `{json.dumps(drift.get('delta_v2_strict_minus_prior') or {}, ensure_ascii=False)}`",
        "",
        "## Measurement loop (operational metacognition)",
        "",
        loop.get("self_evolution_boundary_ko", ""),
        "",
        "**Guardrails learned:**",
    ]
    for g in loop.get("learned_guardrails") or []:
        lines.append(f"- {g}")
    lines.extend(
        [
            "",
            "**Reproduce:** `py scripts/build_logos_passive_drift_governance_v1.py`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-history", action="store_true")
    args = ap.parse_args()

    if not HOLDOUT.is_file() or not OFF_AB.is_file():
        print(f"MISSING inputs: holdout={HOLDOUT.is_file()} off_ab={OFF_AB.is_file()}", flush=True)
        return 2

    doc = build_payload()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(_render_md(doc), encoding="utf-8")

    if not args.no_history:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "generated_at_utc": doc["generated_at_utc"],
            "train_holdout_v2": ((doc["cohorts"]["train_holdout"] or {}).get("raw") or {}).get(
                "v2_btrack_strict"
            ),
            "off_fixture_v2": ((doc["cohorts"]["off_fixture_ab"] or {}).get("raw") or {}).get(
                "v2_btrack_strict"
            ),
            "drift_flags": (doc["drift"] or {}).get("drift_flags") or [],
        }
        with HISTORY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(snapshot, ensure_ascii=False) + "\n")

    print(json.dumps({"ok": True, "out_json": str(OUT_JSON), "drift": doc["drift"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
