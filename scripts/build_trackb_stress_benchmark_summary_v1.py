#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "trackb_stress_benchmark_summary_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _pair_saving_proxy(domain: str) -> dict[str, Any]:
    pair_path = ART / f"trackb_semantic_eval_pairs_{domain}_v1.jsonl"
    rows = _read_jsonl(pair_path)
    src_len = 0
    pred_len = 0
    for row in rows:
        src = str(row.get("source_text", ""))
        pred = str(row.get("predicted_text", ""))
        src_len += max(1, len(src))
        pred_len += max(1, len(pred))
    ratio = pred_len / src_len if src_len > 0 else 1.0
    return {
        "domain": domain,
        "pair_file": str(pair_path.relative_to(ROOT)).replace("\\", "/"),
        "pair_count": len(rows),
        "char_ratio_pred_over_src": round(ratio, 8),
        "saving_ratio_proxy": round(1.0 - ratio, 8),
    }


def _extract_curve_rates(rows: list[dict[str, Any]]) -> tuple[float, float, int]:
    rates: list[float] = []
    sample_count = 0
    for row in rows:
        sample_count += int(row.get("sample_count", 0) or 0)
        if "exact_sequence_match_rate" in row:
            rates.append(float(row["exact_sequence_match_rate"]))
        elif "token_set_match_rate" in row:
            rates.append(float(row["token_set_match_rate"]))
    if not rates:
        return 0.0, 0.0, sample_count
    return min(rates), sum(rates) / len(rates), sample_count


def main() -> int:
    integrity_floor = 0.95
    semantic_floor = 0.80

    weekly = _read_json(ART / "trackb_weekly_gate_recheck_latest.json")
    by_domain = _read_json(ART / "trackb_semantic_eval_by_domain_latest.json")
    stress_base = _read_json(ART / "trackb_quaternion_top_combo_stress_grid_latest.json")
    stress_a = _read_json(ART / "trackb_quaternion_top_combo_stress_grid_exact_robust_split_a_latest.json")
    stress_b1 = _read_json(ART / "trackb_quaternion_top_combo_stress_grid_exact_robust_split_b1_latest.json")
    stress_b2 = _read_json(ART / "trackb_quaternion_top_combo_stress_grid_exact_robust_split_b2_latest.json")
    replay = _read_json(ART / "trackb_quaternion_top_combo_fixed_set_replay_latest.json")
    action = _read_json(ART / "trackb_action_layer_gate_pilot_latest.json")

    # Global measured proxies (config-independent).
    savings_by_domain = [_pair_saving_proxy(d) for d in ("medical", "finance", "policy")]
    global_saving_proxy = sum(x["saving_ratio_proxy"] for x in savings_by_domain) / len(savings_by_domain)
    global_jaccard = (
        sum(float(v["metrics"]["average_semantic_score"]) for v in by_domain["domains"].values())
        / max(1, len(by_domain["domains"]))
    )

    stress_lookup: dict[str, dict[str, Any]] = {}
    for source_name, grid in (
        ("base", stress_base),
        ("extended_split_a", stress_a),
        ("extended_split_b1", stress_b1),
        ("extended_split_b2", stress_b2),
    ):
        for row in grid.get("rows", []):
            artifact = str(row.get("artifact"))
            curve = row.get("stress_curve", []) or []
            min_rate, mean_rate, sample_count = _extract_curve_rates(curve)
            entry = stress_lookup.setdefault(
                artifact,
                {
                    "artifact": artifact,
                    "min_stress_rate_observed": 1.0,
                    "mean_stress_rate_observed_sum": 0.0,
                    "mean_stress_rate_observed_count": 0,
                    "stress_sample_count": 0,
                    "sources": [],
                },
            )
            entry["min_stress_rate_observed"] = min(entry["min_stress_rate_observed"], min_rate)
            entry["mean_stress_rate_observed_sum"] += mean_rate
            entry["mean_stress_rate_observed_count"] += 1
            entry["stress_sample_count"] += sample_count
            entry["sources"].append(source_name)

    candidates: list[dict[str, Any]] = []
    for row in replay.get("rows", []):
        artifact = str(row.get("artifact"))
        stress = stress_lookup.get(artifact, {})
        min_stress_rate = float(stress.get("min_stress_rate_observed", 0.0))
        integrity_ok = min_stress_rate >= integrity_floor
        mean_stress_rate = 0.0
        if int(stress.get("mean_stress_rate_observed_count", 0)) > 0:
            mean_stress_rate = float(stress["mean_stress_rate_observed_sum"]) / float(
                stress["mean_stress_rate_observed_count"]
            )
        candidates.append(
            {
                "artifact": artifact,
                "weights": row.get("config_snapshot", {}).get("weights", {}),
                "stage1_top_k": row.get("config_snapshot", {}).get("stage1_top_k"),
                "beam_size": row.get("config_snapshot", {}).get("beam_size"),
                "block_size": row.get("config_snapshot", {}).get("block_size"),
                "failure_count_at_selection": int(row.get("failure_count_at_selection", 0) or 0),
                "replay_min_short_bucket_rate": float(row.get("replay_min_short_bucket_rate", 0.0) or 0.0),
                "min_stress_rate_observed": round(min_stress_rate, 8),
                "mean_stress_rate_observed": round(mean_stress_rate, 8),
                "stress_sample_count": int(stress.get("stress_sample_count", 0) or 0),
                "integrity_floor_ok": integrity_ok,
                # Config-specific saving metric is not emitted by current Track-B artifacts.
                # Use measured global pair-level saving proxy for sorting priority label.
                "saving_ratio_proxy": round(global_saving_proxy, 8),
                "jaccard_proxy": round(global_jaccard, 8),
            }
        )

    candidates_sorted = sorted(
        candidates,
        key=lambda x: (
            -float(x["saving_ratio_proxy"]),
            -float(x["jaccard_proxy"]),
            -float(x["min_stress_rate_observed"]),
            -int(x["stress_sample_count"]),
            int(x["failure_count_at_selection"]),
            str(x["artifact"]),
        ),
    )
    top3 = candidates_sorted[:3]
    integrity_pass_count = sum(1 for c in candidates if c["integrity_floor_ok"])

    action_summary = action.get("summary", {})
    event_count = max(1, int(action_summary.get("event_count", 0) or 0))
    action_fire_rate = float(action_summary.get("action_fire_count", 0) or 0) / event_count
    fallback_rate = float(action_summary.get("fallback_count", 0) or 0) / event_count

    weekly_go = str(weekly.get("decision", "")) == "GO_RESEARCH"
    semantic_ok = global_jaccard >= semantic_floor
    integrity_ok = integrity_pass_count >= 1
    sensitive_ok = action_fire_rate >= 0.30 and fallback_rate <= 0.70

    if weekly_go and semantic_ok and integrity_ok and sensitive_ok:
        recommendation = "PASS_RESEARCH_LANE"
    elif weekly_go and (semantic_ok or integrity_ok):
        recommendation = "WARN_RESEARCH_LANE"
    else:
        recommendation = "HOLD_RESEARCH_LANE"

    out = {
        "schema": "trackb_stress_benchmark_summary_v1",
        "generated_at_utc": _utc_now(),
        "artifact_inputs": {
            "weekly_gate": "docs/final/artifacts/trackb_weekly_gate_recheck_latest.json",
            "by_domain": "docs/final/artifacts/trackb_semantic_eval_by_domain_latest.json",
            "stress_base": "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_latest.json",
            "stress_split_a": "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_exact_robust_split_a_latest.json",
            "stress_split_b1": "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_exact_robust_split_b1_latest.json",
            "stress_split_b2": "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_exact_robust_split_b2_latest.json",
            "fixed_set_replay": "docs/final/artifacts/trackb_quaternion_top_combo_fixed_set_replay_latest.json",
            "action_gate": "docs/final/artifacts/trackb_action_layer_gate_pilot_latest.json",
        },
        "integrity_constraints": {
            "integrity_hard_floor_min_stress_rate": integrity_floor,
            "semantic_jaccard_floor_global": semantic_floor,
            "sensitive_gate_action_fire_rate_min": 0.30,
            "sensitive_gate_fallback_rate_max": 0.70,
        },
        "global_metrics": {
            "global_saving_ratio_proxy": round(global_saving_proxy, 8),
            "global_jaccard_proxy": round(global_jaccard, 8),
            "sensitive_action_fire_rate": round(action_fire_rate, 8),
            "sensitive_fallback_rate": round(fallback_rate, 8),
            "weekly_gate_decision": weekly.get("decision"),
        },
        "saving_proxy_by_domain": savings_by_domain,
        "candidate_count": len(candidates),
        "integrity_pass_count": integrity_pass_count,
        "objective_order": [
            "saving_ratio_proxy_desc",
            "jaccard_proxy_desc",
            "min_stress_rate_desc",
            "stress_sample_count_desc",
            "failure_count_asc",
        ],
        "top3_candidates": top3,
        "recommendation": recommendation,
        "fact_safe_note": (
            "Saving ratio here is a measured pair-level proxy from static semantic pairs and is "
            "not a per-config compression ratio emitted by current Track-B stress artifacts."
        ),
        "out_of_scope": "No production promotion, no trading trigger.",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
