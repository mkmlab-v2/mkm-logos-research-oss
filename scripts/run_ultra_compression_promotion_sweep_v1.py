#!/usr/bin/env python3
"""Sweep ssot relaxed-cap variants and pick best Track A promotion candidate (RQ-016).

Writes ``docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_PROMOTION_CANDIDATE_V1.json``
and never overwrites ``MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`` unless
``apply_multilens_ultra_compression_track_a_promotion_v1.py`` is run with human approval.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

OUT_CANDIDATE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_PROMOTION_CANDIDATE_V1.json"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
TRACK_A_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
POLICY_FLOOR = 0.47
SSOT_DOMAIN = "ssot"
TOP5_LOW_SAVING_IDS = frozenset({"cmp2_006", "cmp2_004", "cmp2_002", "cmp2_005", "cmp2_009"})
REGRESSION_WATCH_IDS = frozenset({"cmp2_003", "cmp2_005", "cmp2_008", "cmp2_010"})

FORBIDDEN_WRITE = frozenset(
    {
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve(),
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _gms(x: Any) -> float | None:
    return float(x) if x is not None else None


def _case_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = (report.get("compression_metrics") or {}).get("cases") or []
    return {str(c.get("id", "")): c for c in cases}


def _by_id_diff(pin: dict[str, dict[str, Any]], ref: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cid in sorted(set(pin) | set(ref)):
        p = pin.get(cid) or {}
        r = ref.get(cid) or {}
        ps = p.get("token_saving_rate")
        rs = r.get("token_saving_rate")
        pj = p.get("reconstruction_fidelity_jaccard")
        rj = r.get("reconstruction_fidelity_jaccard")
        route_p = p.get("route") or {}
        route_r = r.get("route") or {}
        rows.append(
            {
                "id": cid,
                "domain": route_p.get("domain") or route_r.get("domain"),
                "token_saving_rate_ref": rs,
                "token_saving_rate_pin": ps,
                "delta_saving": (
                    round(float(ps) - float(rs), 6)
                    if ps is not None and rs is not None
                    else None
                ),
                "jaccard_ref": rj,
                "jaccard_pin": pj,
                "delta_jaccard": (
                    round(float(pj) - float(rj), 6) if pj is not None and rj is not None else None
                ),
            }
        )
    return rows


def _promotion_gates(
    *,
    saving: float,
    avg_j: float,
    min_j: float,
    baseline_j: float,
    threshold_pp: float,
    track_a_ref: dict[str, Any] | None,
    degraded_count: int,
    regressing_case_ids: list[str],
) -> dict[str, Any]:
    jaccard_drop_pp = max(0.0, (baseline_j - avg_j) * 100.0)
    ta_min_j = float((track_a_ref or {}).get("min_reconstruction_fidelity_jaccard") or 0)
    floor_ok = saving >= POLICY_FLOOR
    drop_ok = jaccard_drop_pp <= threshold_pp
    min_j_ok = min_j >= ta_min_j - 1e-9 if track_a_ref else False
    no_regression = degraded_count == 0
    regression_only_top5_drag = bool(regressing_case_ids) and all(
        cid in TOP5_LOW_SAVING_IDS for cid in regressing_case_ids
    )
    bench_promotion_eligible = (
        floor_ok and drop_ok and min_j_ok and (no_regression or regression_only_top5_drag)
    )
    auto = bench_promotion_eligible
    return {
        "ultra_saving_policy_ok": floor_ok,
        "jaccard_drop_pp_vs_v2_baseline": round(jaccard_drop_pp, 4),
        "jaccard_drop_within_decision_threshold": drop_ok,
        "min_jaccard_pin": min_j,
        "min_jaccard_not_below_track_a": min_j_ok,
        "cases_with_jaccard_regression_count": degraded_count,
        "regressing_case_ids": regressing_case_ids,
        "regression_confined_to_top5_low_saving": regression_only_top5_drag,
        "bench_promotion_eligible": bench_promotion_eligible,
        "auto_track_a_promotion_allowed": auto,
        "human_review_required": not auto,
        "commander_waiver_eligible": floor_ok and drop_ok and not min_j_ok,
    }


def _eval_variant(
    *,
    src: dict[str, Any],
    sel: dict[str, Any],
    baseline_j: float,
    threshold_pp: float,
    variant_id: str,
    domain_relaxed: dict[str, float],
    case_allowlist: frozenset[str] | None,
    case_exclude: frozenset[str] | None,
    track_a_cases: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    report = evaluate_report(
        src,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=str(sel.get("strategy", "A")),
        intensity=str(sel.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=_gms(sel.get("general_max_saving_rate")),
        sensitive_max_saving_rate=_gms(sel.get("sensitive_max_saving_rate")),
        hangul_max_saving_rate=_gms(sel.get("hangul_max_saving_rate")),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
        apply_gematria_4d_bridge_policy=False,
        bridge_policy_domain_allowlist=None,
        domain_relaxed_max_saving_overrides=domain_relaxed,
        domain_relaxed_max_saving_case_allowlist=case_allowlist,
        domain_relaxed_max_saving_exclude_case_ids=case_exclude,
    )
    cm = report.get("compression_metrics") or {}
    saving = float(cm.get("global_token_saving_rate") or 0)
    avg_j = float(cm.get("avg_reconstruction_fidelity_jaccard") or 0)
    min_j = float(cm.get("min_reconstruction_fidelity_jaccard") or 0)
    by_id: list[dict[str, Any]] = []
    degraded_count = 0
    regressing_ids: list[str] = []
    if track_a_cases is not None:
        by_id = _by_id_diff(_case_map(report), track_a_cases)
        regressing_ids = [
            str(r["id"])
            for r in by_id
            if (r.get("delta_jaccard") or 0) < -1e-9
        ]
        degraded_count = len(regressing_ids)
    track_a_ref = None
    if TRACK_A_ACTIVE.is_file():
        ta = _load(TRACK_A_ACTIVE)
        tacm = ta.get("compression_metrics") or {}
        track_a_ref = {
            "global_token_saving_rate": tacm.get("global_token_saving_rate"),
            "min_reconstruction_fidelity_jaccard": tacm.get("min_reconstruction_fidelity_jaccard"),
        }
    gates = _promotion_gates(
        saving=saving,
        avg_j=avg_j,
        min_j=min_j,
        baseline_j=baseline_j,
        threshold_pp=threshold_pp,
        track_a_ref=track_a_ref,
        degraded_count=degraded_count,
        regressing_case_ids=regressing_ids,
    )
    return {
        "variant_id": variant_id,
        "run_config": {
            "domain_relaxed_max_saving_overrides": domain_relaxed,
            "domain_relaxed_max_saving_case_allowlist": (
                sorted(case_allowlist) if case_allowlist is not None else None
            ),
            "domain_relaxed_max_saving_exclude_case_ids": (
                sorted(case_exclude) if case_exclude is not None else None
            ),
            "apply_gematria_4d_bridge_policy": False,
        },
        "metrics": {
            "global_token_saving_rate": saving,
            "avg_reconstruction_fidelity_jaccard": avg_j,
            "min_reconstruction_fidelity_jaccard": min_j,
        },
        "promotion_gates": gates,
        "by_id_diff_vs_track_a": by_id,
        "report": report,
    }


def _variant_specs() -> list[dict[str, Any]]:
    relaxed_45 = {SSOT_DOMAIN: 0.45}
    relaxed_42 = {SSOT_DOMAIN: 0.42}
    relaxed_40 = {SSOT_DOMAIN: 0.40}
    return [
        {
            "variant_id": "ssot_cap_0.45_global",
            "domain_relaxed": relaxed_45,
            "case_allowlist": None,
            "case_exclude": None,
        },
        {
            "variant_id": "ssot_cap_0.45_top5_allowlist",
            "domain_relaxed": relaxed_45,
            "case_allowlist": TOP5_LOW_SAVING_IDS,
            "case_exclude": None,
        },
        {
            "variant_id": "ssot_cap_0.45_exclude_regression_watch",
            "domain_relaxed": relaxed_45,
            "case_allowlist": None,
            "case_exclude": REGRESSION_WATCH_IDS,
        },
        {
            "variant_id": "ssot_cap_0.45_top5_and_exclude_watch",
            "domain_relaxed": relaxed_45,
            "case_allowlist": TOP5_LOW_SAVING_IDS,
            "case_exclude": REGRESSION_WATCH_IDS,
        },
        {
            "variant_id": "ssot_cap_0.42_global",
            "domain_relaxed": relaxed_42,
            "case_allowlist": None,
            "case_exclude": None,
        },
        {
            "variant_id": "ssot_cap_0.40_top5_allowlist",
            "domain_relaxed": relaxed_40,
            "case_allowlist": TOP5_LOW_SAVING_IDS,
            "case_exclude": None,
        },
    ]


def _rank_key(row: dict[str, Any]) -> tuple:
    g = row.get("promotion_gates") or {}
    m = row.get("metrics") or {}
    auto = 1 if g.get("auto_track_a_promotion_allowed") else 0
    floor = 1 if g.get("ultra_saving_policy_ok") else 0
    min_j_ok = 1 if g.get("min_jaccard_not_below_track_a") else 0
    saving = float(m.get("global_token_saving_rate") or 0)
    min_j = float(m.get("min_reconstruction_fidelity_jaccard") or 0)
    regressions = int(g.get("cases_with_jaccard_regression_count") or 0)
    return (auto, floor, min_j_ok, saving, min_j, -regressions)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_CANDIDATE)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out_path = args.out_json.resolve()
    if out_path in FORBIDDEN_WRITE:
        raise SystemExit("Refusing to write Track A active report from sweep.")

    specs = _variant_specs()
    if args.dry_run:
        print(json.dumps({"dry_run": True, "variants": [s["variant_id"] for s in specs]}, ensure_ascii=False))
        return 0

    src = _load(INPUT_V2)
    base = _load(BASELINE_V2)
    dec = _load(DECISION)
    sel = dec.get("selected_candidate") or {}
    baseline_j = float(base.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0))
    threshold_pp = float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    track_a_cases = _case_map(_load(TRACK_A_ACTIVE)) if TRACK_A_ACTIVE.is_file() else None

    full_rows: list[dict[str, Any]] = []
    for spec in specs:
        full_rows.append(
            _eval_variant(
                src=src,
                sel=sel,
                baseline_j=baseline_j,
                threshold_pp=threshold_pp,
                variant_id=str(spec["variant_id"]),
                domain_relaxed=dict(spec["domain_relaxed"]),
                case_allowlist=spec.get("case_allowlist"),
                case_exclude=spec.get("case_exclude"),
                track_a_cases=track_a_cases,
            )
        )

    winner_full = max(full_rows, key=_rank_key)
    winner = {k: v for k, v in winner_full.items() if k != "report"}
    ranked = sorted(
        ({k: v for k, v in r.items() if k != "report"} for r in full_rows),
        key=_rank_key,
        reverse=True,
    )
    report = winner_full["report"]
    envelope = {
        "schema": "multilens_ultra_compression_promotion_candidate_envelope_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "track_wall": "promotion_candidate_not_active_until_apply",
        "rq": "RQ-016-promotion-sweep",
        "policy_floor": POLICY_FLOOR,
        "selected_variant_id": winner["variant_id"],
        "selected_run_config": winner.get("run_config"),
        "selected_metrics": winner.get("metrics"),
        "selected_promotion_gates": winner.get("promotion_gates"),
        "sweep_ranking": [
            {
                "variant_id": r["variant_id"],
                "metrics": r.get("metrics"),
                "promotion_gates": r.get("promotion_gates"),
            }
            for r in ranked
        ],
        "apply_script": "scripts/apply_multilens_ultra_compression_track_a_promotion_v1.py",
        "promotion_note": (
            "Candidate only. Run apply script with --human-approve-promotion after commander sign-off. "
            "Use --accept-min-j-waiver when auto_track_a_promotion_allowed is false but floor passes."
        ),
    }
    report["promotion_candidate_envelope"] = envelope
    report["active_profile"] = {
        "sla_track": "track_a_promotion_candidate",
        "selected_variant_id": winner["variant_id"],
        "must_apply_via": "scripts/apply_multilens_ultra_compression_track_a_promotion_v1.py",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "selected_variant_id": winner["variant_id"],
                "promotion_gates": winner.get("promotion_gates"),
                "auto_promotion_count": sum(
                    1 for r in ranked if (r.get("promotion_gates") or {}).get("auto_track_a_promotion_allowed")
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
