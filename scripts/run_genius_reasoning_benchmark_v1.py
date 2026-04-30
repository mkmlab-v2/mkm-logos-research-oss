#!/usr/bin/env python3
"""Run a lightweight genius-style reasoning benchmark and emit report artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_WEEKLY = ART / "layer1_layer5_weekly_ops_report_latest.json"
DEFAULT_MICROCOSM = ART / "sasang_microcosm_runtime_assessment_latest.json"
DEFAULT_TASKS = ART / "genius_reasoning_benchmark_tasks_v1.json"
DEFAULT_HUMAN_GOLDSET = ART / "genius_reasoning_human_goldset_v1.json"
DEFAULT_REPORT = ART / "genius_reasoning_benchmark_report_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _default_tasks() -> dict[str, Any]:
    return {
        "schema": "genius_reasoning_benchmark_tasks_v1",
        "generated_at_utc": _iso_now(),
        "tasks": [
            {"task_id": "GR-01", "type": "multi_step_planning", "difficulty": 0.8, "weight": 0.25},
            {"task_id": "GR-02", "type": "counterfactual_reasoning", "difficulty": 0.75, "weight": 0.20},
            {"task_id": "GR-03", "type": "constraint_repair", "difficulty": 0.7, "weight": 0.20},
            {"task_id": "GR-04", "type": "risk_forecast_response", "difficulty": 0.72, "weight": 0.20},
            {"task_id": "GR-05", "type": "novel_pattern_transfer", "difficulty": 0.85, "weight": 0.15},
        ],
    }


def _default_human_goldset() -> dict[str, Any]:
    return {
        "schema": "genius_reasoning_human_goldset_v1",
        "generated_at_utc": _iso_now(),
        "rows": [],
        "note": "Only rows with label_source=human and review_status=approved are used for robust coverage/calibration.",
    }


def _ensure_tasks(path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    tasks = doc.get("tasks") if isinstance(doc.get("tasks"), list) else []
    if tasks:
        return doc
    doc = _default_tasks()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def _ensure_human_goldset(path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    if isinstance(doc, dict) and rows is not None:
        return doc
    doc = _default_human_goldset()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _parse_dt(ts: Any) -> datetime | None:
    if not ts:
        return None
    s = str(ts).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _task_bucket(task_type: str) -> str:
    t = str(task_type or "").strip().lower()
    if any(k in t for k in ("adversarial", "deceptive", "counterexample", "policy_exception")):
        return "safety"
    if any(k in t for k in ("long_horizon", "temporal", "multi_step")):
        return "long_horizon"
    return "general"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weekly-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--microcosm-json", type=Path, default=DEFAULT_MICROCOSM)
    ap.add_argument("--tasks-json", type=Path, default=DEFAULT_TASKS)
    ap.add_argument("--human-goldset-json", type=Path, default=DEFAULT_HUMAN_GOLDSET)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--pass-threshold", type=float, default=0.78)
    ap.add_argument("--min-safety-score", type=float, default=0.74)
    ap.add_argument("--min-long-horizon-score", type=float, default=0.72)
    ap.add_argument("--min-human-coverage", type=float, default=0.30)
    ap.add_argument("--max-calibration-gap", type=float, default=0.20)
    ap.add_argument("--max-human-label-age-days", type=float, default=30.0)
    args = ap.parse_args()

    weekly = _read_json(args.weekly_json)
    microcosm = _read_json(args.microcosm_json)
    tasks_doc = _ensure_tasks(args.tasks_json)
    human_goldset = _ensure_human_goldset(args.human_goldset_json)
    tasks = tasks_doc.get("tasks") if isinstance(tasks_doc.get("tasks"), list) else []

    summary = weekly.get("summary") if isinstance(weekly.get("summary"), dict) else {}
    weekly_pass = str(weekly.get("overall_status") or "") == "PASS"
    integrated_go = str(summary.get("integrated_decision") or "") == "GO_CONTROLLED"
    preflight_go = str(summary.get("emotion_preflight_decision") or "") == "GO_LIVE_CANDIDATE"
    stage = str((microcosm.get("diagnosis") or {}).get("stage") or "unknown")
    risk_band = str((microcosm.get("diagnosis") or {}).get("risk_band") or "unknown")

    stage_bonus = {"stable": 0.08, "early": 0.03, "mid": -0.02, "late": -0.08}.get(stage, -0.03)
    risk_bonus = {"low": 0.06, "medium": 0.0, "high": -0.06}.get(risk_band, -0.03)
    gate_bonus = (0.06 if weekly_pass else -0.08) + (0.04 if integrated_go else -0.06) + (0.03 if preflight_go else -0.05)

    rows: list[dict[str, Any]] = []
    bucket_scores: dict[str, list[float]] = {"general": [], "safety": [], "long_horizon": []}
    weighted = 0.0
    weight_sum = 0.0
    for t in tasks:
        if not isinstance(t, dict):
            continue
        task_id = str(t.get("task_id") or "")
        difficulty = float(t.get("difficulty") or 0.7)
        weight = float(t.get("weight") or 0.2)
        base = 0.92 - 0.28 * difficulty
        score = _clip(base + stage_bonus + risk_bonus + gate_bonus, 0.0, 1.0)
        rows.append(
            {
                "task_id": task_id,
                "type": t.get("type"),
                "difficulty": difficulty,
                "weight": weight,
                "score": round(score, 4),
                "pass": bool(score >= float(args.pass_threshold)),
            }
        )
        bucket_scores[_task_bucket(str(t.get("type") or ""))].append(score)
        weighted += score * weight
        weight_sum += weight

    final = weighted / weight_sum if weight_sum > 0 else 0.0

    human_rows = human_goldset.get("rows") if isinstance(human_goldset.get("rows"), list) else []
    expected_map: dict[str, float] = {}
    for row in human_rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("label_source") or "").strip().lower() != "human":
            continue
        if str(row.get("review_status") or "").strip().lower() != "approved":
            continue
        task_id = str(row.get("task_id") or "").strip()
        if not task_id:
            continue
        try:
            expected_map[task_id] = _clip(float(row.get("expected_score") or 0.0), 0.0, 1.0)
        except (TypeError, ValueError):
            continue
    now_utc = datetime.now(timezone.utc)
    approved_ages_days: list[float] = []
    stale_approved_count = 0
    for row in human_rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("label_source") or "").strip().lower() != "human":
            continue
        if str(row.get("review_status") or "").strip().lower() != "approved":
            continue
        dt = _parse_dt(row.get("reviewed_at_utc"))
        if dt is None:
            continue
        age_days = max(0.0, (now_utc - dt).total_seconds() / 86400.0)
        approved_ages_days.append(age_days)
        if age_days > float(args.max_human_label_age_days):
            stale_approved_count += 1

    covered = 0
    gap_sum = 0.0
    for r in rows:
        task_id = str(r.get("task_id") or "")
        if task_id in expected_map:
            covered += 1
            gap_sum += abs(float(r.get("score") or 0.0) - float(expected_map[task_id]))
    task_count = len(rows)
    coverage = float(covered) / float(task_count) if task_count > 0 else 0.0
    calibration_gap = float(gap_sum) / float(covered) if covered > 0 else 0.0
    realism_penalty = 0.0
    if coverage < float(args.min_human_coverage):
        realism_penalty += _clip(float(args.min_human_coverage) - coverage, 0.0, 1.0) * 0.30
    if covered > 0 and calibration_gap > float(args.max_calibration_gap):
        realism_penalty += _clip(calibration_gap - float(args.max_calibration_gap), 0.0, 1.0) * 0.30
    stale_ratio = (float(stale_approved_count) / float(len(approved_ages_days))) if approved_ages_days else 0.0
    if stale_ratio > 0.0:
        realism_penalty += _clip(stale_ratio, 0.0, 1.0) * 0.20
    robust_score = _clip(final - realism_penalty, 0.0, 1.0)
    coverage_gate_pass = coverage >= float(args.min_human_coverage)
    freshness_gate_pass = stale_approved_count == 0
    robust_status = "PASS" if (robust_score >= float(args.pass_threshold) and coverage_gate_pass and freshness_gate_pass) else "HOLD"
    safety_avg = sum(bucket_scores["safety"]) / float(len(bucket_scores["safety"])) if bucket_scores["safety"] else final
    long_avg = (
        sum(bucket_scores["long_horizon"]) / float(len(bucket_scores["long_horizon"]))
        if bucket_scores["long_horizon"]
        else final
    )
    subscore_gate_pass = (safety_avg >= float(args.min_safety_score)) and (long_avg >= float(args.min_long_horizon_score))

    out = {
        "schema": "genius_reasoning_benchmark_report_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "weekly_json": str(args.weekly_json).replace("\\", "/"),
            "microcosm_json": str(args.microcosm_json).replace("\\", "/"),
            "tasks_json": str(args.tasks_json).replace("\\", "/"),
            "human_goldset_json": str(args.human_goldset_json).replace("\\", "/"),
        },
        "controls": {
            "weekly_pass": weekly_pass,
            "integrated_go": integrated_go,
            "preflight_go": preflight_go,
            "microcosm_stage": stage,
            "microcosm_risk_band": risk_band,
            "pass_threshold": float(args.pass_threshold),
            "min_safety_score": float(args.min_safety_score),
            "min_long_horizon_score": float(args.min_long_horizon_score),
            "min_human_coverage": float(args.min_human_coverage),
            "max_calibration_gap": float(args.max_calibration_gap),
            "max_human_label_age_days": float(args.max_human_label_age_days),
        },
        "task_results": rows,
        "robustness": {
            "human_coverage": round(coverage, 4),
            "calibration_gap": round(calibration_gap, 4),
            "stale_approved_count": int(stale_approved_count),
            "stale_approved_ratio": round(stale_ratio, 4),
            "max_approved_label_age_days": round(max(approved_ages_days), 4) if approved_ages_days else 0.0,
            "realism_penalty": round(realism_penalty, 4),
            "coverage_gate_pass": coverage_gate_pass,
            "freshness_gate_pass": freshness_gate_pass,
            "robust_score": round(robust_score, 4),
            "robust_score_100": round(robust_score * 100.0, 1),
            "robust_benchmark_status": robust_status,
        },
        "subscores": {
            "general_score": round((sum(bucket_scores["general"]) / float(len(bucket_scores["general"]))) if bucket_scores["general"] else final, 4),
            "safety_score": round(safety_avg, 4),
            "long_horizon_score": round(long_avg, 4),
            "subscore_gate_pass": subscore_gate_pass,
        },
        "summary": {
            "task_count": len(rows),
            "pass_count": sum(1 for r in rows if r.get("pass")),
            "weighted_score": round(final, 4),
            "weighted_score_100": round(final * 100.0, 1),
            "benchmark_status": "PASS" if (final >= float(args.pass_threshold) and subscore_gate_pass) else "HOLD",
        },
        "note": "This benchmark is an operational proxy for high-order reasoning quality and should evolve with real graded tasks.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "weighted_score_100": out["summary"]["weighted_score_100"],
                "benchmark_status": out["summary"]["benchmark_status"],
                "robust_score_100": out["robustness"]["robust_score_100"],
                "robust_benchmark_status": out["robustness"]["robust_benchmark_status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
