#!/usr/bin/env python3
"""Aggregate B-track v1_price_only research candidate into a human-review packet (research_only).

Does NOT apply ensemble profile to prod score JSON or enable Track A / live trading.
LG outcome independent — documents freeze + shield + Phase 3 pointer.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTO_OPT = ROOT / "reports/btrack_prophecy_auto_optimal_combo_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/btrack_ensemble_fusion_ablation_v1_latest.json"
DEFAULT_FAIR = ROOT / "reports/prophecy_lens_ensemble_vs_multilens_fair_compare_v1_latest.json"
DEFAULT_HOLDOUT = ROOT / "reports/btrack_holdout_gate_candidate_v1_latest.json"
DEFAULT_HIT = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/btrack_v1_price_only_human_review_pack_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/btrack_v1_price_only_human_review_pack_v1_latest.md"
SCHEMA = "btrack_v1_price_only_human_review_pack_v1"
PROFILE = "v1_price_only"
ALERT1 = 0.5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else str(path)


def _find_candidate(candidates: list[dict[str, Any]], *, profile: str, window: str) -> dict[str, Any] | None:
    for c in candidates:
        if c.get("profile") == profile and str(c.get("window")) == window:
            return c
        cid = str(c.get("candidate_id") or "")
        if profile in cid and str(c.get("window")) == window:
            return c
    return None


def _fusion_row(doc: dict[str, Any] | None, profile: str) -> dict[str, Any] | None:
    if not doc:
        return None
    for row in doc.get("rows") or []:
        if isinstance(row, dict) and row.get("profile") == profile:
            return row
    return None


def _decision_block(
    *,
    prod_30: dict[str, Any] | None,
    cand_30: dict[str, Any] | None,
    cand_180: dict[str, Any] | None,
) -> dict[str, Any]:
    def _hr(doc: dict[str, Any] | None) -> float | None:
        if not doc:
            return None
        m = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else doc
        v = m.get("price_directional_hit_rate")
        return float(v) if v is not None else None

    p30 = _hr(prod_30)
    c30 = _hr(cand_30)
    c180 = _hr(cand_180)
    alert_30 = c30 is not None and c30 >= ALERT1
    alert_180 = c180 is not None and c180 >= ALERT1
    apply_prod = False
    track_a = False
    if alert_30 and alert_180:
        human_decision = "HOLD_REVIEW_BOTH_WINDOWS_PASS_ABLATION_ONLY"
        reason = "Ablation windows pass ALERT_1 but prod path, holdout7, WF not re-signed."
    elif alert_180 and not alert_30:
        human_decision = "HOLD_REVIEW_180_ONLY"
        reason = "180d ablation passes; 30d still below coin-flip floor — no prod apply."
    else:
        human_decision = "REJECT_APPLY"
        reason = "ALERT_1 not met on 30d (required for near-term ops); research memo only."
    return {
        "apply_to_prod_score_json": apply_prod,
        "track_a_promotion": track_a,
        "auto_promote": False,
        "human_decision": human_decision,
        "reason_ko": reason,
        "alert_1_threshold": ALERT1,
        "candidate_profile": PROFILE,
    }


def _render_md(payload: dict[str, Any]) -> str:
    m = payload.get("metrics") or {}
    d = payload.get("decision") or {}
    sh = payload.get("defensive_shield") or {}
    lines = [
        "# B-track v1_price_only — Human review pack (research_only)",
        "",
        f"- generated: `{payload.get('generated_at_utc')}`",
        f"- LG-independent freeze line: **prod engine frozen; Phase 3 leading sensors next**",
        "",
        "## Headline numbers",
        "",
        f"| Window | Prod | v1_price_only (ablation rebuild) | ALERT_1 (50%) |",
        f"|--------|------|----------------------------------|---------------|",
        f"| 30d | {m.get('prod_30d_hit_rate', 'n/a')} | {m.get('candidate_30d_hit_rate', 'n/a')} | "
        f"{'PASS' if m.get('candidate_30d_alert_1_pass') else 'FAIL'} |",
        f"| 180d | {m.get('prod_180d_hit_rate', 'n/a')} | {m.get('candidate_180d_hit_rate', 'n/a')} | "
        f"{'PASS' if m.get('candidate_180d_alert_1_pass') else 'FAIL'} |",
        "",
        "## Decision (human)",
        "",
        f"- **apply_to_prod:** `{d.get('apply_to_prod_score_json')}`",
        f"- **track_a:** `{d.get('track_a_promotion')}`",
        f"- **verdict:** `{d.get('human_decision')}`",
        f"- {d.get('reason_ko', '')}",
        "",
        "## Defensive shield (unchanged headline)",
        "",
        f"- holdout7 neutralized: `{sh.get('holdout7_neutralized', 'n/a')}/7`",
        f"- train_wrong_dir neutralized: `{sh.get('train_wrong_dir_neutralized', 'n/a')}`",
        f"- gate slug: `{sh.get('gate_slug', 'n/a')}`",
        "",
        "## Next (Phase 3 — RQ-020)",
        "",
        "- Leading sensors ingest (order flow / on-chain / funding) — not more OHLCV knob tuning.",
        "- Real per-date myeongni/sasang JSONL; multilens as size/confidence aux only.",
        "",
        f"Rerun: `py scripts/build_btrack_v1_price_only_human_review_pack_v1.py`",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--auto-optimal", type=Path, default=DEFAULT_AUTO_OPT)
    ap.add_argument("--fusion-ablation", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--fair-compare", type=Path, default=DEFAULT_FAIR)
    ap.add_argument("--holdout-gate", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--hit-eval", type=Path, default=DEFAULT_HIT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    ap.add_argument("--skip-md", action="store_true")
    args = ap.parse_args(argv)

    auto = _load(args.auto_optimal)
    fusion = _load(args.fusion_ablation)
    fair = _load(args.fair_compare)
    holdout = _load(args.holdout_gate)
    hit = _load(args.hit_eval)

    candidates = list(auto.get("candidates") or []) if auto else []
    rec = auto.get("recommendations") if isinstance(auto.get("recommendations"), dict) else {}

    prod_30 = rec.get("prod_baseline_30d") or _find_candidate(candidates, profile="prod", window="30")
    if prod_30 is None:
        for c in candidates:
            if c.get("candidate_id") == "prod_baseline_30":
                prod_30 = c
                break

    prod_180 = rec.get("prod_baseline_180d")
    cand_30 = rec.get("best_ensemble_profile_30d") or _find_candidate(candidates, profile=PROFILE, window="30")
    cand_180 = rec.get("best_ensemble_profile_180d") or _find_candidate(candidates, profile=PROFILE, window="180")

    if cand_30 and cand_30.get("profile") != PROFILE:
        cand_30 = _find_candidate(candidates, profile=PROFILE, window="30")
    if cand_180 and cand_180.get("profile") != PROFILE:
        cand_180 = _find_candidate(candidates, profile=PROFILE, window="180")

    fusion_row = _fusion_row(fusion, PROFILE)

    hold7_n = None
    train_n = None
    gate_slug = None
    if holdout:
        h7 = holdout.get("holdout7") if isinstance(holdout.get("holdout7"), dict) else {}
        tw = holdout.get("train_wrong_dir") if isinstance(holdout.get("train_wrong_dir"), dict) else {}
        hold7_n = h7.get("n_holdout7_wrong_neutralized")
        train_n = tw.get("n_train_wrong_neutralized")
        layer = holdout.get("candidate_layer") if isinstance(holdout.get("candidate_layer"), dict) else {}
        gate_slug = layer.get("slug")

    fair_note = None
    if fair:
        fair_note = fair.get("verdict_ko") or fair.get("summary_ko")

    metrics: dict[str, Any] = {
        "prod_30d_hit_rate": prod_30.get("price_directional_hit_rate") if prod_30 else None,
        "prod_180d_hit_rate": prod_180.get("price_directional_hit_rate") if prod_180 else None,
        "candidate_30d_hit_rate": cand_30.get("price_directional_hit_rate") if cand_30 else None,
        "candidate_180d_hit_rate": cand_180.get("price_directional_hit_rate") if cand_180 else None,
        "candidate_30d_uplift_vs_prod": None,
        "candidate_30d_alert_1_pass": bool(cand_30 and cand_30.get("alert_1_pass")),
        "candidate_180d_alert_1_pass": bool(cand_180 and cand_180.get("alert_1_pass")),
        "fusion_ablation_30d_hit_rate": fusion_row.get("price_directional_hit_rate") if fusion_row else None,
    }
    if metrics["prod_30d_hit_rate"] is not None and metrics["candidate_30d_hit_rate"] is not None:
        metrics["candidate_30d_uplift_vs_prod"] = round(
            float(metrics["candidate_30d_hit_rate"]) - float(metrics["prod_30d_hit_rate"]), 6
        )

    decision = _decision_block(prod_30=prod_30, cand_30=cand_30, cand_180=cand_180)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "lg_outcome_assumption": "independent_proceed_as_hold",
        "freeze_line_ko": (
            "OHLCV·neutral_bps 추가 스윕 중단. 본 패킷은 연구 후보 문서화만. "
            "Track A·실매매 스위치 OFF."
        ),
        "inputs": {
            k: _rel(v)
            for k, v in {
                "auto_optimal": args.auto_optimal,
                "fusion_ablation": args.fusion_ablation,
                "fair_compare": args.fair_compare,
                "holdout_gate": args.holdout_gate,
                "hit_eval": args.hit_eval,
            }.items()
            if v.is_file()
        },
        "metrics": metrics,
        "decision": decision,
        "defensive_shield": {
            "gate_slug": gate_slug,
            "holdout7_neutralized": hold7_n,
            "train_wrong_dir_neutralized": train_n,
            "headline_unchanged_on_prod_rows": True,
            "note_ko": "방패는 post-ensemble 보조층; prod ALERT_1 헤드라인은 그대로.",
        },
        "fair_compare_note": fair_note,
        "hit_eval_headline": None,
        "phase3_pointer": {
            "rq_id": "RQ-020",
            "chain": "scripts/run_btrack_phase3_leading_sensors_chain_v1.py",
            "next_actions_ko": [
                "선행 센서 JSONL ingest 스텁→실측 교체",
                "stub 캘린더 렌즈 → run_lens_myeongni/run_lens_sasang per-date",
                "멀티렌즈는 size/confidence 보조 ablation만",
            ],
        },
        "operator_lines": [
            f"- [MKM-HR-PACK] v1_price_only apply={decision['apply_to_prod_score_json']} track_a={decision['track_a_promotion']}",
            f"- [MKM-HR-PACK] prod_30d={metrics.get('prod_30d_hit_rate')} cand_30d={metrics.get('candidate_30d_hit_rate')} "
            f"ALERT1_30={'PASS' if metrics.get('candidate_30d_alert_1_pass') else 'FAIL'}",
            f"- [MKM-HR-PACK] cand_180d={metrics.get('candidate_180d_hit_rate')} "
            f"ALERT1_180={'PASS' if metrics.get('candidate_180d_alert_1_pass') else 'FAIL'}",
            f"- [MKM-HR-PACK] shield holdout7={hold7_n}/7 train_wrong={train_n}",
        ],
        "rerun": "py scripts/build_btrack_v1_price_only_human_review_pack_v1.py",
    }
    if hit:
        hm = hit.get("metrics") if isinstance(hit.get("metrics"), dict) else {}
        payload["hit_eval_headline"] = hm.get("price_directional_hit_rate")

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.skip_md:
        args.out_md.write_text(_render_md(payload), encoding="utf-8")

    print(f"WROTE: {args.out_json.resolve()}")
    if not args.skip_md:
        print(f"WROTE: {args.out_md.resolve()}")
    print(f"DECISION={decision['human_decision']} apply_prod={decision['apply_to_prod_score_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
