"""Shared ops dynamical bench L0/L1 helpers [HYPO · B-track]."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

from scripts.ops_dynamical_ty_geumhwa_link_v1 import build_ty_geumhwa_link_v1  # noqa: E402

DEFAULT_OUT = ROOT / "reports/ops_dynamical_bench_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports/ops_dynamical_timeseries_v1.jsonl"

THRESHOLDS_SOURCE = "mkm_theory_mathematization_canon_v1 §5 병증약리 stress bands"
STAGE_BANDS = (
    ("calm", 0.35),
    ("watch", 0.55),
    ("stress", 0.75),
    ("crisis", 1.01),
)
STAGE_ORDER = {"calm": 0, "watch": 1, "stress": 2, "crisis": 3}

INPUT_PATHS = (
    "reports/reddit_agent_run_v1_latest.json",
    "reports/mkm_solo_background_ops_state.json",
    "reports/mkm_cursor_session_upgrade_v1_latest.json",
)

DEFAULT_HORIZON_MINUTES = 10


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def load_json_rel(rel: str) -> dict[str, Any] | None:
    path = ROOT / rel.replace("/", "\\")
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None


def stage_from_stress(score: float) -> str:
    for name, upper in STAGE_BANDS:
        if score < upper:
            return name
    return "crisis"


def predict_stage(current: str, stress: float) -> tuple[str, float]:
    if current == "crisis":
        return "crisis", 0.85
    if stress >= 0.55:
        return "crisis", 0.55
    if stress >= 0.35:
        return "stress", 0.5
    return "watch", 0.4


def submit_tab_count(reddit: dict[str, Any] | None) -> int:
    if not reddit:
        return 0
    for step in reddit.get("steps") or []:
        inv = (step.get("summary") or {}).get("submit_tab_invariant") or step.get("submit_tab_invariant")
        if isinstance(inv, dict):
            return int(inv.get("submit_tabs_after") or inv.get("submit_tabs_before") or 0)
    pre = reddit.get("preflight") or {}
    inv2 = pre.get("submit_tab_invariant") or {}
    if isinstance(inv2, dict):
        return int(inv2.get("submit_tabs_after") or inv2.get("submit_tabs_before") or 0)
    return 0


def compute_stress(
    *,
    submit_tabs: int,
    solo_ok: bool | None,
    upgrade_ok: bool | None,
    reddit_ok: bool | None,
) -> tuple[float, dict[str, float]]:
    parts: list[float] = []
    if submit_tabs > 1:
        parts.append(min(1.0, 0.35 + 0.25 * (submit_tabs - 1)))
    if solo_ok is False:
        parts.append(0.22)
    if upgrade_ok is False:
        parts.append(0.18)
    if reddit_ok is False:
        parts.append(0.15)
    score = min(1.0, sum(parts)) if parts else 0.12
    slkm = {
        "S": min(1.0, 0.15 + score * 0.85),
        "L": min(1.0, max(0.0, 0.55 - score * 0.35)),
        "K": min(1.0, max(0.0, 0.45 - score * 0.25)),
        "M": min(1.0, 0.25 + score * 0.55),
    }
    return score, slkm


def build_report(*, prior_stress: float | None = None, fractal_level: str = "L0_isomorphism") -> dict[str, Any]:
    inputs_meta: list[dict[str, Any]] = []
    reddit = load_json_rel(INPUT_PATHS[0])
    solo = load_json_rel(INPUT_PATHS[1])
    upgrade = load_json_rel(INPUT_PATHS[2])

    for rel in INPUT_PATHS:
        inputs_meta.append({"path": rel.replace("\\", "/"), "present": (ROOT / rel).is_file()})

    submit_tabs = submit_tab_count(reddit)
    solo_ok = solo.get("last_ok") if solo else None
    upgrade_ok = upgrade.get("ok") if upgrade else None
    reddit_ok = reddit.get("ok") if reddit else None

    stress_score, slkm = compute_stress(
        submit_tabs=submit_tabs,
        solo_ok=solo_ok if isinstance(solo_ok, bool) else None,
        upgrade_ok=upgrade_ok if isinstance(upgrade_ok, bool) else None,
        reddit_ok=reddit_ok if isinstance(reddit_ok, bool) else None,
    )
    stage = stage_from_stress(stress_score)
    pred_stage, pred_conf = predict_stage(stage, stress_score)
    delta = None if prior_stress is None else round(stress_score - prior_stress, 4)
    stamp = utc_now()

    ty_geumhwa_link = build_ty_geumhwa_link_v1(
        slkm=slkm,
        stress_score=stress_score,
        stage=stage,
        solo_ok=solo_ok if isinstance(solo_ok, bool) else None,
        reddit_ok=reddit_ok if isinstance(reddit_ok, bool) else None,
    )

    return {
        "schema": "ops_dynamical_bench_v1",
        "version": "1.0.0",
        "generated_at_utc": stamp,
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fractal_level": fractal_level,
        "domain": "ops_agent",
        "matching_layer_ack": "pedagogical_isomorphism_only — not structural physics identity",
        "state_machine": {
            "stage": stage,
            "thresholds_source": THRESHOLDS_SOURCE,
            "prior_stage": stage_from_stress(prior_stress) if prior_stress is not None else None,
            "delta_stress": delta,
        },
        "proxies": {
            "plane": "mixed",
            "metrics": {
                "reddit_submit_tabs": {"value": submit_tabs, "unit": "count", "note": "R1 invariant max=1"},
                "solo_ops_last_ok": {
                    "value": 1 if solo_ok else 0 if solo_ok is False else -1,
                    "unit": "bool01_or_unknown",
                },
                "cursor_session_upgrade_ok": {
                    "value": 1 if upgrade_ok else 0 if upgrade_ok is False else -1,
                    "unit": "bool01_or_unknown",
                },
                "reddit_governed_ok": {
                    "value": 1 if reddit_ok else 0 if reddit_ok is False else -1,
                    "unit": "bool01_or_unknown",
                },
            },
        },
        "stress": {
            "score": round(stress_score, 4),
            "formula_id": "ops_stress_v1_weighted_proxy",
            "slkm_overlay": {k: round(v, 4) for k, v in slkm.items()},
        },
        "prediction": {
            "horizon_minutes": DEFAULT_HORIZON_MINUTES,
            "predicted_stage": pred_stage,
            "confidence": pred_conf,
        },
        "validation": {
            "observed_stage": None,
            "timing_error_minutes": None,
            "intervention_applied": False,
            "intervention_ok": None,
        },
        "inputs": inputs_meta,
        "governance": {"reddit_r1_r6": True, "dual_plane_non_merge": True},
        "ty_sparsity_geumhwa_link_v1": ty_geumhwa_link,
        "ok": True,
        "reproduce": "py scripts/run_ops_dynamical_bench_v1.py",
    }


def timeseries_row_from_bench(
    bench: dict[str, Any],
    *,
    intervention: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema": "ops_dynamical_timeseries_row_v1",
        "recorded_at_utc": bench["generated_at_utc"],
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "domain": bench.get("domain", "ops_agent"),
        "stage": bench["state_machine"]["stage"],
        "stress_score": bench["stress"]["score"],
        "prediction": dict(bench.get("prediction") or {}),
        "proxies": bench.get("proxies", {}).get("metrics", {}),
        "source": "run_ops_dynamical_bench_v1",
    }
    if intervention is not None:
        row["intervention"] = intervention
    return row


def append_jsonl_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def stage_rank(stage: str) -> int:
    return STAGE_ORDER.get(stage, -1)


def eval_l1_pairs(
    rows: list[dict[str, Any]],
    *,
    horizon_minutes: float = DEFAULT_HORIZON_MINUTES,
) -> dict[str, Any]:
    pairs: list[dict[str, Any]] = []
    for i, origin in enumerate(rows):
        pred = origin.get("prediction") or {}
        predicted_stage = pred.get("predicted_stage")
        if not predicted_stage:
            continue
        t0 = parse_utc(origin["recorded_at_utc"])
        target = t0.timestamp() + horizon_minutes * 60.0
        observed_row = None
        for later in rows[i + 1 :]:
            if parse_utc(later["recorded_at_utc"]).timestamp() >= target:
                observed_row = later
                break
        if observed_row is None:
            pairs.append(
                {
                    "origin_at_utc": origin["recorded_at_utc"],
                    "predicted_stage": predicted_stage,
                    "observed_stage": None,
                    "stage_exact_match": None,
                    "stage_rank_delta": None,
                    "timing_error_minutes": None,
                    "status": "pending_horizon",
                }
            )
            continue
        observed_stage = observed_row["stage"]
        exact = predicted_stage == observed_stage
        rank_delta = abs(stage_rank(predicted_stage) - stage_rank(observed_stage))
        obs_ts = parse_utc(observed_row["recorded_at_utc"]).timestamp()
        timing_err = round((obs_ts - target) / 60.0, 2)
        pairs.append(
            {
                "origin_at_utc": origin["recorded_at_utc"],
                "observed_at_utc": observed_row["recorded_at_utc"],
                "predicted_stage": predicted_stage,
                "observed_stage": observed_stage,
                "stage_exact_match": exact,
                "stage_rank_delta": rank_delta,
                "timing_error_minutes": timing_err,
                "status": "evaluated",
            }
        )

    evaluated = [p for p in pairs if p["status"] == "evaluated"]
    pending = [p for p in pairs if p["status"] == "pending_horizon"]
    exact_rate = None
    mean_rank_delta = None
    mean_timing_err = None
    if evaluated:
        exact_rate = round(sum(1 for p in evaluated if p["stage_exact_match"]) / len(evaluated), 4)
        mean_rank_delta = round(sum(p["stage_rank_delta"] or 0 for p in evaluated) / len(evaluated), 4)
        mean_timing_err = round(
            sum(abs(p["timing_error_minutes"] or 0.0) for p in evaluated) / len(evaluated),
            4,
        )

    return {
        "schema": "ops_dynamical_l1_eval_v1",
        "version": "1.0.0",
        "generated_at_utc": utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fractal_level": "L1_prediction",
        "horizon_minutes": horizon_minutes,
        "rows_total": len(rows),
        "pairs_total": len(pairs),
        "pairs_evaluated": len(evaluated),
        "pairs_pending_horizon": len(pending),
        "metrics": {
            "stage_exact_match_rate": exact_rate,
            "mean_stage_rank_delta": mean_rank_delta,
            "mean_abs_timing_error_minutes": mean_timing_err,
        },
        "pairs": pairs,
        "ok": True,
        "reproduce": "py scripts/run_ops_dynamical_l1_eval_v1.py",
    }


def _intervention_applied(row: dict[str, Any]) -> bool:
    inv = row.get("intervention") or {}
    return bool(inv.get("applied"))


def eval_l2_interventions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pairs: list[dict[str, Any]] = []
    for i in range(1, len(rows)):
        after = rows[i]
        if not _intervention_applied(after):
            continue
        before = rows[i - 1]
        inv = after.get("intervention") or {}
        stress_before = float(before.get("stress_score", 0))
        stress_after = float(after.get("stress_score", 0))
        stress_delta = round(stress_after - stress_before, 4)
        rank_before = stage_rank(before.get("stage", ""))
        rank_after = stage_rank(after.get("stage", ""))
        rank_delta = rank_after - rank_before
        improved = stress_delta < 0 or rank_delta < 0
        equilibrium = stress_after < STAGE_BANDS[0][1] or (improved and rank_after <= rank_before)
        pairs.append(
            {
                "before_at_utc": before.get("recorded_at_utc"),
                "after_at_utc": after.get("recorded_at_utc"),
                "intervention_kind": inv.get("kind"),
                "intervention_ok": inv.get("ok"),
                "stage_before": before.get("stage"),
                "stage_after": after.get("stage"),
                "stress_before": stress_before,
                "stress_after": stress_after,
                "stress_delta": stress_delta,
                "stage_rank_delta": rank_delta,
                "improved": improved,
                "equilibrium_restored": equilibrium,
                "status": "evaluated",
            }
        )

    evaluated = [p for p in pairs if p["status"] == "evaluated"]
    restore_rate = None
    mean_stress_delta = None
    if evaluated:
        restore_rate = round(
            sum(1 for p in evaluated if p["equilibrium_restored"]) / len(evaluated),
            4,
        )
        mean_stress_delta = round(sum(p["stress_delta"] for p in evaluated) / len(evaluated), 4)

    return {
        "schema": "ops_dynamical_l2_eval_v1",
        "version": "1.0.0",
        "generated_at_utc": utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fractal_level": "L2_intervention",
        "rows_total": len(rows),
        "pairs_total": len(pairs),
        "pairs_evaluated": len(evaluated),
        "metrics": {
            "equilibrium_restore_rate": restore_rate,
            "mean_stress_delta": mean_stress_delta,
        },
        "pairs": pairs,
        "ok": True,
        "reproduce": "py scripts/run_ops_dynamical_l2_eval_v1.py",
    }


def synthetic_bench_override(
    *,
    stage: str,
    stress_score: float,
    fractal_level: str = "L2_intervention",
) -> dict[str, Any]:
    """Build bench-shaped doc with explicit stage/stress for L2 fixtures."""
    doc = build_report(fractal_level=fractal_level)
    doc["state_machine"]["stage"] = stage
    doc["stress"]["score"] = round(stress_score, 4)
    pred_stage, pred_conf = predict_stage(stage, stress_score)
    doc["prediction"] = {
        "horizon_minutes": DEFAULT_HORIZON_MINUTES,
        "predicted_stage": pred_stage,
        "confidence": pred_conf,
    }
    return doc


L3_DOMAIN_PATHS: dict[str, Path] = {
    "ops_agent": ROOT / "reports/ops_dynamical_bench_v1_latest.json",
    "music_p1": ROOT / "reports/dual_plane_music_p1_micro_bench_v1_latest.json",
    "spatial_p2": ROOT / "reports/dual_plane_spatial_p2_micro_bench_v1_latest.json",
    "p3_merkle": ROOT / "reports/dual_plane_p3_merkle_audit_micro_bench_v1_latest.json",
}

L3_BENCH_RUNNERS: dict[str, str] = {
    "music_p1": "scripts/run_dual_plane_music_p1_micro_bench_v1.py",
    "spatial_p2": "scripts/run_dual_plane_spatial_p2_micro_bench_v1.py",
    "p3_merkle": "scripts/run_dual_plane_p3_merkle_audit_micro_bench_v1.py",
}


def normalize_dual_plane_profile(
    doc: dict[str, Any],
    *,
    domain_id: str,
    raw_key: str,
    post_key: str,
    delta_key: str,
) -> dict[str, Any]:
    metrics = doc.get("metrics") or {}
    raw = float(metrics[raw_key])
    post = float(metrics[post_key])
    delta = metrics.get(delta_key)
    if delta is None:
        delta = round(post - raw, 6)
    else:
        delta = float(delta)
    collapsed = metrics.get("collapsed_combined_score")
    return {
        "domain_id": domain_id,
        "artifact_schema": doc.get("schema"),
        "plane_model": "dual_plane_neuro_symbolic",
        "raw_plane_rate": round(raw, 6),
        "symbolic_plane_rate": round(post, 6),
        "delta_post_minus_raw": delta,
        "collapsed_combined_score": collapsed,
        "stage": stage_from_stress(raw),
        "symbolic_equilibrium": post == 0.0,
        "non_merge_policy_ok": collapsed is None,
        "improved_or_flat": delta is None or float(delta) <= 0.0,
    }


def normalize_ops_profile(doc: dict[str, Any]) -> dict[str, Any]:
    stress = float((doc.get("stress") or {}).get("score", 0.12))
    metrics = (doc.get("proxies") or {}).get("metrics") or {}
    submit_tabs = int((metrics.get("reddit_submit_tabs") or {}).get("value", 0))
    gov = doc.get("governance") or {}
    symbolic_residual = 0.0 if submit_tabs <= 1 and gov.get("reddit_r1_r6") else min(1.0, stress)
    validation = doc.get("validation") or {}
    if validation.get("equilibrium_restored"):
        symbolic_residual = min(symbolic_residual, 0.1)
    return {
        "domain_id": "ops_agent",
        "artifact_schema": doc.get("schema"),
        "plane_model": "dual_plane_neuro_symbolic",
        "raw_plane_rate": round(stress, 6),
        "symbolic_plane_rate": round(symbolic_residual, 6),
        "delta_post_minus_raw": round(symbolic_residual - stress, 6),
        "collapsed_combined_score": None,
        "stage": doc.get("state_machine", {}).get("stage") or stage_from_stress(stress),
        "symbolic_equilibrium": symbolic_residual == 0.0,
        "non_merge_policy_ok": True,
        "improved_or_flat": symbolic_residual <= stress,
    }


def load_l3_profiles(paths: dict[str, Path] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    paths = paths or L3_DOMAIN_PATHS
    profiles: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for domain_id, path in paths.items():
        if not path.is_file():
            missing.append({"domain_id": domain_id, "path": str(path).replace("\\", "/")})
            continue
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        if domain_id == "ops_agent":
            profiles.append(normalize_ops_profile(doc))
        elif domain_id == "music_p1":
            profiles.append(
                normalize_dual_plane_profile(
                    doc,
                    domain_id=domain_id,
                    raw_key="raw_neural_illegal_rate",
                    post_key="post_project_illegal_rate",
                    delta_key="delta_post_minus_raw_illegal_rate",
                )
            )
        elif domain_id == "spatial_p2":
            profiles.append(
                normalize_dual_plane_profile(
                    doc,
                    domain_id=domain_id,
                    raw_key="raw_neural_violation_rate",
                    post_key="post_project_violation_rate",
                    delta_key="delta_post_minus_raw_violation_rate",
                )
            )
        elif domain_id == "p3_merkle":
            profiles.append(
                normalize_dual_plane_profile(
                    doc,
                    domain_id=domain_id,
                    raw_key="raw_tamper_undetected_rate",
                    post_key="post_merkle_tamper_undetected_rate",
                    delta_key="delta_post_minus_raw_tamper_undetected_rate",
                )
            )
        else:
            missing.append({"domain_id": domain_id, "path": str(path), "error": "unknown_domain"})
    return profiles, missing


def eval_l3_cross_fixture(profiles: list[dict[str, Any]], *, missing: list[dict[str, Any]]) -> dict[str, Any]:
    required_keys = {
        "domain_id",
        "plane_model",
        "raw_plane_rate",
        "symbolic_plane_rate",
        "collapsed_combined_score",
        "stage",
        "symbolic_equilibrium",
        "non_merge_policy_ok",
    }
    checks: list[dict[str, Any]] = []

    def add(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"check_id": check_id, "pass": passed, "detail": detail})

    add("domains_present_4", len(profiles) == 4, f"profiles={len(profiles)} missing={len(missing)}")
    add("missing_empty", len(missing) == 0, f"missing={missing}")
    if profiles:
        models = {p["plane_model"] for p in profiles}
        add("plane_model_unified", models == {"dual_plane_neuro_symbolic"}, f"models={sorted(models)}")
        add(
            "structure_keys_match",
            all(required_keys <= set(p.keys()) for p in profiles),
            "required_keys_present",
        )
        add(
            "non_merge_policy_all",
            all(p.get("non_merge_policy_ok") for p in profiles),
            "collapsed_combined_score null policy",
        )
        add(
            "symbolic_equilibrium_all",
            all(p.get("symbolic_equilibrium") for p in profiles),
            "symbolic_plane_rate==0 for all domains",
        )
        add(
            "improved_or_flat_all",
            all(p.get("improved_or_flat") for p in profiles),
            "delta_post_minus_raw <= 0",
        )
        stages = [p.get("stage") for p in profiles]
        add("stage_machine_shared_vocabulary", all(s in STAGE_ORDER for s in stages), f"stages={stages}")

    passed = sum(1 for c in checks if c["pass"])
    total = len(checks)
    isomorphism_score = round(passed / total, 4) if total else 0.0

    return {
        "schema": "ops_dynamical_l3_eval_v1",
        "version": "1.0.0",
        "generated_at_utc": utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fractal_level": "L3_cross_domain",
        "domains_expected": list(L3_DOMAIN_PATHS.keys()),
        "domains_present": [p["domain_id"] for p in profiles],
        "missing_artifacts": missing,
        "profiles": profiles,
        "checks": checks,
        "checks_pass_count": passed,
        "checks_total": total,
        "metrics": {
            "isomorphism_score": isomorphism_score,
            "symbolic_equilibrium_rate": round(
                sum(1 for p in profiles if p.get("symbolic_equilibrium")) / len(profiles), 4
            )
            if profiles
            else None,
            "mean_raw_plane_rate": round(sum(p["raw_plane_rate"] for p in profiles) / len(profiles), 4)
            if profiles
            else None,
        },
        "ok": passed == total and total > 0,
        "reproduce": "py scripts/run_ops_dynamical_l3_cross_fixture_eval_v1.py",
    }


L4_COHORT_GATE_PATH = ROOT / "reports/han_vocology_km_vhi_pilot_cohort_gate_v1_latest.json"
L4_L3_PREREQ_PATH = ROOT / "reports/ops_dynamical_l3_eval_v1_latest.json"
L4_REGISTERED_ENDPOINT = "km_vhi_total_delta_pct_week8"
L4_MIN_COHORTS = 3


def clinical_stage_from_band(band: str | None, delta: float | None) -> str:
    if band == "excellent":
        return "calm"
    if band == "partial":
        return "watch"
    if band == "non_responder":
        return "crisis"
    if band == "between_partial_non_responder":
        return "stress"
    if delta is not None:
        if delta >= 20:
            return "calm"
        if delta >= 10:
            return "watch"
        if delta <= -10:
            return "crisis"
        if delta < 0:
            return "stress"
    return "watch"


def normalize_clinical_cohort_profile(cohort: dict[str, Any]) -> dict[str, Any]:
    band = cohort.get("band_week8")
    delta_raw = cohort.get("delta_pct_week8")
    delta = float(delta_raw) if delta_raw is not None else None
    stage = clinical_stage_from_band(band if isinstance(band, str) else None, delta)
    if band == "excellent":
        raw, symbolic = 0.55, 0.0
    elif band == "partial":
        raw, symbolic = 0.65, 0.25
    elif band == "non_responder":
        raw, symbolic = 0.85, 0.75
    elif band == "between_partial_non_responder":
        raw, symbolic = 0.72, 0.45
    else:
        raw = max(0.1, min(1.0, 0.6 - (delta or 0) / 100.0))
        symbolic = 0.0 if stage == "calm" else min(1.0, raw * 0.3)
    return {
        "pseudonym_id": cohort.get("pseudonym_id"),
        "domain_id": "clinical_track_b",
        "artifact_schema": "han_vocology_km_vhi_pilot_cohort_gate_v1",
        "plane_model": "dual_plane_neuro_symbolic",
        "registered_endpoint": L4_REGISTERED_ENDPOINT,
        "raw_plane_rate": round(raw, 6),
        "symbolic_plane_rate": round(symbolic, 6),
        "delta_post_minus_raw": round(symbolic - raw, 6),
        "collapsed_combined_score": None,
        "stage": stage,
        "band_week8": band,
        "delta_pct_week8": delta,
        "symbolic_equilibrium": symbolic == 0.0,
        "non_merge_policy_ok": True,
        "improved_or_flat": delta is None or delta >= 0 or band == "excellent",
    }


def load_l4_inputs(
    *,
    cohort_gate_path: Path | None = None,
    l3_prereq_path: Path | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]]]:
    gate_path = cohort_gate_path or L4_COHORT_GATE_PATH
    l3_path = l3_prereq_path or L4_L3_PREREQ_PATH
    gate_doc = None
    l3_doc = None
    if gate_path.is_file():
        gate_doc = json.loads(gate_path.read_text(encoding="utf-8-sig"))
    if l3_path.is_file():
        l3_doc = json.loads(l3_path.read_text(encoding="utf-8-sig"))
    profiles: list[dict[str, Any]] = []
    if gate_doc:
        for cohort in gate_doc.get("cohorts") or []:
            profiles.append(normalize_clinical_cohort_profile(cohort))
    return gate_doc, l3_doc, profiles


def eval_l4_clinical_cohort(
    *,
    gate_doc: dict[str, Any] | None,
    l3_doc: dict[str, Any] | None,
    profiles: list[dict[str, Any]],
    missing: list[dict[str, Any]],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"check_id": check_id, "pass": passed, "detail": detail})

    l3_ok = bool(l3_doc and l3_doc.get("ok"))
    add("l3_prerequisite_ok", l3_ok, f"l3_ok={l3_ok}")
    add("missing_empty", len(missing) == 0, f"missing={missing}")

    track_b = gate_doc is not None and gate_doc.get("track") == "B"
    add("track_b_only", track_b, f"track={gate_doc.get('track') if gate_doc else None}")

    send_hold = gate_doc is not None and gate_doc.get("send_gate") == "HOLD"
    add("send_gate_hold", send_hold, f"send_gate={gate_doc.get('send_gate') if gate_doc else None}")

    cohort_count = int((gate_doc or {}).get("cohort_count") or len(profiles))
    add("cohort_count_min", cohort_count >= L4_MIN_COHORTS, f"cohort_count={cohort_count}")

    with_w8 = int((gate_doc or {}).get("cohorts_with_week8") or sum(1 for p in profiles if p.get("delta_pct_week8") is not None))
    coverage = round(with_w8 / cohort_count, 4) if cohort_count else 0.0
    add("endpoint_coverage", coverage >= 0.5, f"coverage={coverage}")

    add(
        "registered_endpoint_km_vhi",
        all(p.get("registered_endpoint") == L4_REGISTERED_ENDPOINT for p in profiles),
        L4_REGISTERED_ENDPOINT,
    )
    stages = [p.get("stage") for p in profiles]
    add("stage_vocabulary_shared", all(s in STAGE_ORDER for s in stages), f"stages={stages[:5]}...")
    add(
        "non_merge_policy_all",
        all(p.get("non_merge_policy_ok") and p.get("collapsed_combined_score") is None for p in profiles),
        "no merged clinical+ops KPI",
    )

    excellent = int((gate_doc or {}).get("excellent_at_week8") or sum(1 for p in profiles if p.get("band_week8") == "excellent"))
    eq_rate = round(excellent / with_w8, 4) if with_w8 else None
    add(
        "equilibrium_analog_rate",
        eq_rate is not None and eq_rate >= 0.5,
        f"excellent_at_week8={excellent} with_w8={with_w8} rate={eq_rate}",
    )

    deltas = [p["delta_pct_week8"] for p in profiles if p.get("delta_pct_week8") is not None]
    mean_delta = round(sum(deltas) / len(deltas), 4) if deltas else None

    passed = sum(1 for c in checks if c["pass"])
    total = len(checks)
    clinical_epsilon_score = round(passed / total, 4) if total else 0.0

    return {
        "schema": "ops_dynamical_l4_eval_v1",
        "version": "1.0.0",
        "generated_at_utc": utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fractal_level": "L4_clinical_cohort",
        "track": "B",
        "patient_facing": "blocked",
        "registered_endpoint": L4_REGISTERED_ENDPOINT,
        "clinical_pilot_source": "han_vocology_km_vhi_pilot",
        "l3_prerequisite": {
            "path": str(L4_L3_PREREQ_PATH).replace("\\", "/"),
            "ok": l3_ok,
            "isomorphism_score": (l3_doc or {}).get("metrics", {}).get("isomorphism_score"),
        },
        "cohort_gate": {
            "path": str(L4_COHORT_GATE_PATH).replace("\\", "/"),
            "cohort_count": cohort_count,
            "cohorts_with_week8": with_w8,
            "excellent_at_week8": excellent,
        },
        "missing_artifacts": missing,
        "profiles": profiles,
        "checks": checks,
        "checks_pass_count": passed,
        "checks_total": total,
        "metrics": {
            "clinical_epsilon_score": clinical_epsilon_score,
            "endpoint_coverage_rate": coverage,
            "equilibrium_analog_rate": eq_rate,
            "mean_delta_pct_week8": mean_delta,
            "symbolic_equilibrium_rate": round(
                sum(1 for p in profiles if p.get("symbolic_equilibrium")) / len(profiles), 4
            )
            if profiles
            else None,
        },
        "disclaimer": "HYPO education pilot — not clinical efficacy · IRB · send_gate release",
        "ok": passed == total and total > 0 and l3_ok,
        "reproduce": "py scripts/run_ops_dynamical_l4_clinical_eval_v1.py",
    }
