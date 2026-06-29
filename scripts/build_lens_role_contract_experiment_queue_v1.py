#!/usr/bin/env python3
"""Build B-layer role-contract fail analysis + next experiment queue [HYPO][research_only].

Reads three_lens_horizon_empirical_eval_v2 + lens_sovereignty_report_v1_2.
Emits structured root-cause rows and HITL experiment items — no auto-apply.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "lens_role_contract_experiment_queue_v1"
DEFAULT_HORIZON = ROOT / "docs/final/artifacts/three_lens_horizon_empirical_eval_v2_latest.json"
DEFAULT_SOVEREIGNTY = ROOT / "docs/final/artifacts/lens_sovereignty_report_v1_2_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/lens_role_contract_experiment_queue_v1_latest.json"
DEFAULT_HITL = ROOT / "docs/final/artifacts/evolution_sovereignty_hitl_queue_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _myeongni_fail_analysis(grid: dict[str, Any]) -> dict[str, Any]:
    rates = grid.get("rate_by_horizon") if isinstance(grid.get("rate_by_horizon"), dict) else {}
    ranked = grid.get("ranked_by_soft_hit_rate") if isinstance(grid.get("ranked_by_soft_hit_rate"), list) else []
    contract = str(grid.get("contract_horizon") or "mid_10d")
    contract_rate = float((rates.get(contract) or {}).get("soft_hit_rate") or 0.0)
    best_h = str(grid.get("best_horizon") or "")
    best_rate = float(grid.get("best_soft_hit_rate") or 0.0)
    delta = float(grid.get("soft_delta_best_minus_contract") or 0.0)

    flat_grid = all(
        abs(float((rates.get(h) or {}).get("soft_hit_rate") or 0.5) - 0.5) < 0.002
        for h in rates
    )

    if flat_grid:
        root_cause = "flat_coin_flip_grid"
        root_cause_ko = (
            "명리 independent 채널이 5~21d 전 구간 soft_hit ≈ 50% — "
            "horizon 선택 문제가 아니라 방향 신호 자체가 패널에서 flat."
        )
    elif delta < 0.005:
        root_cause = "wrong_contract_horizon_marginal"
        root_cause_ko = (
            f"계약 {contract}({contract_rate:.4f}) vs 최적 {best_h}({best_rate:.4f}) "
            f"차이 {delta:.4f} — 미세; horizon 재라벨 검토."
        )
    else:
        root_cause = "wrong_contract_horizon_clear"
        root_cause_ko = f"계약 {contract} 대비 {best_h} 우세 (Δ={delta:.4f})."

    return {
        "lens_id": "myeongni",
        "operational_role": "mid_horizon_direction",
        "contract_horizon": contract,
        "contract_soft_hit_rate": contract_rate,
        "best_horizon": best_h,
        "best_soft_hit_rate": best_rate,
        "contract_is_best": bool(grid.get("contract_is_best")),
        "contract_horizon_rank": grid.get("contract_horizon_rank"),
        "ranked_horizons": ranked,
        "rate_by_horizon": rates,
        "root_cause_id": root_cause,
        "root_cause_ko": root_cause_ko,
        "supplementary_note": (
            "weather/prophecy supplementary rail SUPP_ALIGNED — "
            "도메인 SSOT 통과 ≠ KOSPI mid-horizon direction."
        ),
    }


def _logos_fail_analysis(
    v1_align: dict[str, Any],
    logos_eval: dict[str, Any],
) -> dict[str, Any]:
    per_lens = (v1_align.get("per_lens") or {}).get("logos") if isinstance(v1_align.get("per_lens"), dict) else {}
    per_variant = logos_eval.get("per_variant") if isinstance(logos_eval.get("per_variant"), dict) else {}
    rate_matrix = logos_eval.get("rate_matrix") if isinstance(logos_eval.get("rate_matrix"), dict) else {}
    cov = logos_eval.get("macro_risk_coverage") if isinstance(logos_eval.get("macro_risk_coverage"), dict) else {}

    best_var = str(logos_eval.get("best_variant_by_macro_soft") or "")
    best_block = per_variant.get(best_var) if isinstance(per_variant.get(best_var), dict) else {}
    causal_pass = bool(best_block.get("macro_alignment_pass_effective"))

    v1_soft = float(per_lens.get("matched_soft_hit_rate") or 0.0) if per_lens else 0.0
    causal_soft = float(best_block.get("matched_soft_hit_rate") or 0.0)

    backfill_rate = float(cov.get("research_backfill_rate") or 0.0)
    operational_rate = float(cov.get("operational_causal_rate") or 0.0)

    if causal_pass and v1_soft < 0.48:
        root_cause = "eval_path_global_snapshot_not_causal"
        root_cause_ko = (
            f"v1 alignment은 global snapshot(21d={v1_soft:.4f}) 기준 fail — "
            f"인과 macro_risk 변종 {best_var}(21d={causal_soft:.4f})는 pass. "
            "헤드라인 role fail ≠ per-date causal 경로 무능."
        )
    elif backfill_rate > 0.9:
        root_cause = "macro_risk_backfill_dominance"
        root_cause_ko = (
            f"macro_risk coverage: operational_causal={operational_rate:.4f}, "
            f"research_backfill={backfill_rate:.4f} — "
            "인과 게이트 실운영 커버리지 부족; backfill 비중 과다."
        )
    else:
        root_cause = "macro_21d_underperforms_short"
        root_cause_ko = (
            f"macro_21d({v1_soft:.4f}) < short_1d mismatch — "
            "거시 horizon 정렬 미달."
        )

    return {
        "lens_id": "logos",
        "operational_role": "macro_non_gating",
        "contract_horizon": "macro_21d",
        "v1_global_snapshot_macro_21d_soft": v1_soft,
        "best_variant_by_macro_soft": best_var,
        "best_variant_macro_21d_soft": causal_soft,
        "best_variant_macro_alignment_pass": causal_pass,
        "rate_matrix_summary": {
            k: v.get("macro_21d") for k, v in rate_matrix.items() if isinstance(v, dict)
        },
        "macro_risk_coverage": cov,
        "logos_per_date_jsonl": logos_eval.get("logos_per_date_jsonl"),
        "root_cause_id": root_cause,
        "root_cause_ko": root_cause_ko,
        "supplementary_note": (
            "chronology supplementary rail pass — era blind/Brier는 KOSPI macro gate와 격벽."
        ),
    }


def _sasang_caveat(intensity: dict[str, Any]) -> dict[str, Any]:
    spearman = float(intensity.get("spearman_rank_corr") or 0.0)
    dec = (intensity.get("variants") or {}).get("decoupled_psych_only") or {}
    dec_spearman = dec.get("spearman_rank_corr")
    mechanical = spearman > 0.99
    dec_mechanical = isinstance(dec_spearman, (int, float)) and float(dec_spearman) > 0.99
    return {
        "lens_id": "sasang",
        "operational_role": "short_intensity_stress",
        "intensity_pass": bool(intensity.get("intensity_pass")),
        "spearman_rank_corr": spearman,
        "decoupled_psych_only_spearman": dec_spearman,
        "mechanical_proxy_suspect": mechanical,
        "decoupled_mechanical_proxy_suspect": dec_mechanical,
        "caveat_ko": (
            "Spearman≈1.0 — machine_readables 스트레스 vs 실현 변동성 proxy 중복 의심. "
            "pass는 유지하되 promotion 근거로 단독 사용 금지."
            if mechanical
            else "intensity gate pass — proxy sanity OK."
        ),
    }


def _experiment_items(
    myeongni: dict[str, Any],
    logos: dict[str, Any],
    sasang: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    ts = _utc_now()

    if not myeongni.get("contract_is_best"):
        items.append(
            {
                "id": "exp_myeongni_direction_signal_v1",
                "lens_id": "myeongni",
                "priority": "P0",
                "kind": "btrack_research_experiment",
                "requires_human_approval": True,
                "auto_apply": False,
                "hypothesis": "명리 independent KOSPI 방향 flat — weather/session fusion 또는 Pack0-B LoRA가 mid-horizon lift 제공",
                "root_cause_id": myeongni.get("root_cause_id"),
                "suggested_commands": [
                    "scripts/Run-BtrackSessionPanelWeatherCorrChain_v1.ps1 (full 1996-2026 window)",
                    "scripts/Run-Pack0bOrderedTrain_v1.ps1 -SkipSmoke (myeongri deterministic LoRA)",
                    "py scripts/run_three_lens_horizon_empirical_eval_v2.py --myeongni-momentum-window 5|10|15",
                ],
                "pass_criterion": "myeongni_horizon_grid.contract_is_best OR mid_10d soft_hit > 0.52 with n>=7235",
                "recorded_at_utc": ts,
            }
        )

    if logos.get("root_cause_id") in (
        "eval_path_global_snapshot_not_causal",
        "macro_risk_backfill_dominance",
    ):
        items.append(
            {
                "id": "exp_logos_causal_macro_path_v1",
                "lens_id": "logos",
                "priority": "P0",
                "kind": "btrack_research_experiment",
                "requires_human_approval": True,
                "auto_apply": False,
                "hypothesis": "role fail은 global snapshot 경로 artifact — per-date causal macro_risk + logos jsonl 재빌드로 재평가",
                "root_cause_id": logos.get("root_cause_id"),
                "suggested_commands": [
                    "py scripts/run_three_lens_horizon_empirical_eval_v2.py --instrument kospi "
                    "--date-from 1996-12-11 --date-to 2026-06-05 (omit --no-logos-jsonl)",
                    "Operational macro_risk forward log coverage 확대 (research_backfill 비중 축소)",
                ],
                "pass_criterion": (
                    "logos_per_date_eval.best_variant macro_alignment_pass_effective "
                    "AND operational_causal_rate > 0.05"
                ),
                "recorded_at_utc": ts,
            }
        )
    elif not logos.get("best_variant_macro_alignment_pass"):
        items.append(
            {
                "id": "exp_logos_macro_horizon_v1",
                "lens_id": "logos",
                "priority": "P1",
                "kind": "btrack_research_experiment",
                "requires_human_approval": True,
                "auto_apply": False,
                "hypothesis": "macro_21d contract horizon 재정렬 또는 trailing regime variant 승격",
                "root_cause_id": logos.get("root_cause_id"),
                "suggested_commands": [
                    "py scripts/run_three_lens_horizon_empirical_eval_v2.py --instrument kospi",
                ],
                "pass_criterion": "macro_21d soft_hit > best short mismatch + 0.03",
                "recorded_at_utc": ts,
            }
        )

    if sasang.get("mechanical_proxy_suspect"):
        items.append(
            {
                "id": "exp_sasang_intensity_proxy_audit_v1",
                "lens_id": "sasang",
                "priority": "P1",
                "kind": "btrack_research_experiment",
                "requires_human_approval": True,
                "auto_apply": False,
                "hypothesis": "Spearman 0.9998 — intensity label과 predictor feature leakage 감사",
                "root_cause_id": "mechanical_intensity_proxy",
                "suggested_commands": [
                    "py scripts/run_three_lens_horizon_empirical_eval_v2.py (intensity_horizon_days sweep 3/5/7)",
                    "Independent holdout: emotion_weight_memory weekly corr (forward PnL) as non-KOSPI rail",
                ],
                "pass_criterion": "spearman_rank_corr < 0.95 on held-out dates OR alert_pass with legacy_prec gate",
                "recorded_at_utc": ts,
            }
        )

    return items


def build_queue(
    *,
    horizon_path: Path,
    sovereignty_path: Path,
    root: Path,
) -> dict[str, Any]:
    horizon = _load(horizon_path)
    sovereignty = _load(sovereignty_path)

    grid = horizon.get("myeongni_horizon_grid") if isinstance(horizon.get("myeongni_horizon_grid"), dict) else {}
    logos_eval = horizon.get("logos_per_date_eval") if isinstance(horizon.get("logos_per_date_eval"), dict) else {}
    v1_align = (horizon.get("v1_direction_eval") or {}).get("alignment_verdict") or {}
    intensity = horizon.get("sasang_intensity_eval") if isinstance(horizon.get("sasang_intensity_eval"), dict) else {}

    myeongni = _myeongni_fail_analysis(grid)
    logos = _logos_fail_analysis(v1_align, logos_eval)
    sasang = _sasang_caveat(intensity)

    role_verdict = sovereignty.get("role_contract_verdict") or "UNKNOWN"
    experiments = _experiment_items(myeongni, logos, sasang)

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "RESEARCH_ONLY_HYPO_B",
        "requires_human_approval": True,
        "auto_apply": False,
        "inputs": {
            "horizon_eval": str(horizon_path.resolve()),
            "sovereignty_report": str(sovereignty_path.resolve()),
        },
        "role_contract_verdict": role_verdict,
        "b_layer_summary_table": [
            {
                "lens": "사상",
                "role": "단기 강도/스트ress",
                "b_layer_pass": bool(intensity.get("intensity_pass")),
                "headline_metric": f"Spearman={intensity.get('spearman_rank_corr')}",
                "interpretation": sasang.get("caveat_ko"),
            },
            {
                "lens": "명리",
                "role": "중기 방향 (mid_10d)",
                "b_layer_pass": bool(grid.get("contract_is_best")),
                "headline_metric": f"mid_10d={grid.get('contract_soft_hit_rate')} best={grid.get('best_horizon')}",
                "interpretation": myeongni.get("root_cause_ko"),
            },
            {
                "lens": "성경(Logos)",
                "role": "거시 macro_21d [NON_GATING]",
                "b_layer_pass": bool(
                    (logos_eval.get("per_variant") or {})
                    .get(logos_eval.get("best_variant_by_macro_soft") or {}, {})
                    .get("macro_alignment_pass_effective")
                ),
                "headline_metric": (
                    f"v1_snapshot_21d={logos.get('v1_global_snapshot_macro_21d_soft')} "
                    f"causal_21d={logos.get('best_variant_macro_21d_soft')}"
                ),
                "interpretation": logos.get("root_cause_ko"),
            },
        ],
        "fail_analysis": {
            "myeongni": myeongni,
            "logos": logos,
            "sasang_caveat": sasang,
        },
        "experiments": experiments,
        "n_experiments": len(experiments),
        "promotion_ready": False,
        "note": "B-layer queue only — does not modify Track A, Commander, or Pack 0-B weights automatically.",
    }


def merge_hitl_queue(queue_path: Path, experiments: list[dict[str, Any]]) -> None:
    existing = _load(queue_path)
    items = list(existing.get("items") or []) if isinstance(existing.get("items"), list) else []
    exp_ids = {e.get("id") for e in experiments}
    items = [i for i in items if i.get("id") not in exp_ids]
    for exp in experiments:
        items.append(
            {
                "id": exp.get("id"),
                "kind": "role_contract_experiment",
                "field": exp.get("lens_id"),
                "requires_human_approval": True,
                "auto_apply": False,
                "suggested_action": "review_experiment_queue",
                "experiment": exp,
                "recorded_at_utc": exp.get("recorded_at_utc"),
            }
        )
    items = items[-80:]
    doc = {
        "schema": "evolution_sovereignty_hitl_queue_v1",
        "updated_at_utc": _utc_now(),
        "research_only": True,
        "items": items,
    }
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--horizon", type=Path, default=DEFAULT_HORIZON)
    ap.add_argument("--sovereignty", type=Path, default=DEFAULT_SOVEREIGNTY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--merge-hitl-queue", action="store_true")
    ap.add_argument("--hitl-queue", type=Path, default=DEFAULT_HITL)
    ns = ap.parse_args()
    root = ns.workspace_root.resolve()

    def _p(p: Path) -> Path:
        return p if p.is_absolute() else root / p

    if not _p(ns.horizon).is_file():
        print(f"MISSING horizon eval: {_p(ns.horizon)}")
        return 1

    doc = build_queue(
        horizon_path=_p(ns.horizon),
        sovereignty_path=_p(ns.sovereignty),
        root=root,
    )
    out = _p(ns.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if ns.merge_hitl_queue and doc.get("experiments"):
        merge_hitl_queue(_p(ns.hitl_queue), doc["experiments"])

    print(f"WROTE: {out.resolve()} n_experiments={doc['n_experiments']} role={doc['role_contract_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
