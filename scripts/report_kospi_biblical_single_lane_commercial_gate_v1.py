# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.9, K:0.5, M:0.7}
# Balance: 89
# Purpose: Report commercialization gate status for KOSPI biblical-only lane.
# Keywords: biblical, KOSPI, gate, commercial, external reality
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ART = Path("docs/final/artifacts")
WF_DEFAULT = ART / "kospi_biblical_wf_gates_v1_latest.json"
LOCK_DEFAULT = ART / "biblical_external_reality_lock_latest.json"
STABILITY_DEFAULT = ART / "biblical_external_dualgate_stability_v1_latest.json"
PROMOTION_DEFAULT = ART / "kospi_biblical_lane_promotion_report_v1_latest.json"
OUT_DEFAULT = ART / "kospi_biblical_single_lane_commercial_gate_v1_latest.json"
LOG_DEFAULT = ART / "kospi_biblical_single_lane_commercial_gate_v1_log.jsonl"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0


def _pred_stats_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pred_counts = Counter(str(r.get("predicted_direction", "UNKNOWN")) for r in rows)
    n = len(rows)
    dominant_share = _safe_div(max(pred_counts.values()) if pred_counts else 0, n)
    return {
        "n_samples": n,
        "predicted_counts": dict(pred_counts),
        "dominant_share": round(dominant_share, 6),
    }


def _row_dominant_share(row: dict[str, Any]) -> float | None:
    counts = row.get("backfill_pred_counts") or {}
    total = sum(int(v) for v in counts.values())
    if total <= 0:
        return None
    return round(max(int(v) for v in counts.values()) / total, 6)


def _aggregate_promotion_internal(promotion: dict[str, Any], rand_baseline: float) -> dict[str, Any] | None:
    folds = promotion.get("walk_forward_folds") or []
    if not folds:
        return None

    total_n = 0
    weighted_acc = 0.0
    weighted_rand = 0.0
    pred_counts: Counter[str] = Counter()
    for fold in folds:
        split = fold.get("split") or {}
        n_test = int(split.get("n_test", 0))
        leader = fold.get("leader_subject_to_min_holdout_test") or fold.get("leader_by_train_then_test_order") or {}
        test = leader.get("test") or {}
        acc = float(test.get("accuracy", 0.0))
        total_n += n_test
        weighted_acc += acc * n_test
        baseline = float((fold.get("reference_baselines_reported_leader") or {}).get("random_3way_baseline", rand_baseline))
        weighted_rand += baseline * n_test
        pred = test.get("counts_predicted") or {}
        for k, v in pred.items():
            pred_counts[str(k)] += int(v)

    if total_n <= 0:
        return None
    acc = weighted_acc / total_n
    rand = weighted_rand / total_n
    dom = (max(pred_counts.values()) / sum(pred_counts.values())) if pred_counts else 1.0
    return {
        "accuracy": round(acc, 6),
        "n_samples": total_n,
        "margin_vs_random": round(acc - rand, 6),
        "dominant_share": round(dom, 6),
        "predicted_counts": dict(pred_counts),
        "source": "walk_forward_folds_aggregated",
    }


def _extract_external_recent(lock_or_gate: dict[str, Any], rand_baseline: float) -> dict[str, Any]:
    # Supports both:
    # 1) lock schema: gate_snapshot.mixed_mode
    # 2) direct gate schema: observed / external_reality_pass
    if "gate_snapshot" in lock_or_gate:
        mixed = (lock_or_gate.get("gate_snapshot") or {}).get("mixed_mode") or {}
        obs = mixed.get("observed") or {}
        rows = obs.get("recent_rows") or []
        stats = _pred_stats_from_rows(rows)
        acc = float(obs.get("recent_accuracy", 0.0))
        n = int(obs.get("n_recent_samples", stats["n_samples"]))
        ext_pass = bool(mixed.get("external_reality_pass", mixed.get("pass", False)))
        return {
            "accuracy": acc,
            "n_samples": n,
            "margin_vs_random": round(acc - rand_baseline, 6),
            "dominant_share": float(stats["dominant_share"]),
            "predicted_counts": stats["predicted_counts"],
            "external_reality_pass": ext_pass,
            "mixed_bull_capture": float(obs.get("recent_bull_capture", 0.0)),
            "source": "lock_mixed_mode",
        }

    obs = lock_or_gate.get("observed") or {}
    rows = obs.get("recent_rows") or []
    stats = _pred_stats_from_rows(rows)
    acc = float(obs.get("recent_accuracy", 0.0))
    n = int(obs.get("n_recent_samples", stats["n_samples"]))
    return {
        "accuracy": acc,
        "n_samples": n,
        "margin_vs_random": round(acc - rand_baseline, 6),
        "dominant_share": float(stats["dominant_share"]),
        "predicted_counts": stats["predicted_counts"],
        "external_reality_pass": bool(lock_or_gate.get("external_reality_pass", False)),
        "mixed_bull_capture": float(obs.get("recent_bull_capture", 0.0)),
        "source": "direct_external_gate",
    }


def build_report(
    wf_json: Path,
    lock_json: Path,
    stability_json: Path,
    promotion_json: Path,
    min_n: int,
    min_accuracy: float,
    min_margin: float,
    max_dominant_share: float,
    enable_recent_adaptive_dominant_cap: bool = True,
    recent_adaptive_cap: float = 0.74,
    recent_adaptive_min_accuracy: float = 0.50,
    recent_adaptive_min_bull_capture: float = 0.15,
) -> dict[str, Any]:
    wf = _load_json(wf_json)
    lock = _load_json(lock_json)
    stability = _load_json(stability_json)
    promotion = _load_json(promotion_json) if promotion_json.exists() else {}

    wf_test = wf["biblical_only_path"]["test_metrics"]
    wf_rand = float(
        (((wf.get("protocol") or {}).get("baselines_on_test") or {}).get("random_3way_baseline", 1.0 / 3.0))
    )
    wf_acc = float(wf_test["accuracy"])
    wf_n = int(wf_test["n_months"])
    wf_margin = round(wf_acc - float(wf_rand), 6)
    wf_dom = round(max(wf_test["counts_predicted"].values()) / wf_n, 6) if wf_n else 1.0
    promo_internal = _aggregate_promotion_internal(promotion, float(wf_rand))

    ext_recent = _extract_external_recent(lock, float(wf_rand))

    # Equivalent-sample view from yearly backfill rows (n >= min_n)
    eq_candidates: list[dict[str, Any]] = []
    for row in stability.get("rows", []):
        n_rows = int(row.get("n_rows", 0))
        if n_rows < min_n:
            continue
        acc = float(row.get("mixed_accuracy", 0.0))
        margin = round(acc - float(wf_rand), 6)
        dom = _row_dominant_share(row)
        eq_candidates.append(
            {
                "year": int(row["year"]),
                "n_samples": n_rows,
                "accuracy": acc,
                "margin_vs_random": margin,
                "dominant_share": dom,
                "mixed_bull_capture": float(row.get("mixed_bull_capture", 0.0)),
                "dual_pass": bool(row.get("dual_pass", False)),
            }
        )
    eq_best = max(eq_candidates, key=lambda x: (x["accuracy"], x["n_samples"]), default=None)
    external_primary = dict(ext_recent)
    external_primary["mode"] = "recent"
    if ext_recent["n_samples"] < min_n and eq_best:
        external_primary = {
            "accuracy": float(eq_best["accuracy"]),
            "n_samples": int(eq_best["n_samples"]),
            "margin_vs_random": float(eq_best["margin_vs_random"]),
            # If equivalent dominant share is unknown, keep recent dominant share (conservative)
            "dominant_share": float(eq_best["dominant_share"]) if eq_best["dominant_share"] is not None else float(ext_recent["dominant_share"]),
            "predicted_counts": ext_recent["predicted_counts"],
            "external_reality_pass": bool(ext_recent["external_reality_pass"]),
            "mixed_bull_capture": float(eq_best.get("mixed_bull_capture", ext_recent["mixed_bull_capture"])),
            "source": "equivalent_n_fallback",
            "mode": "equivalent_n",
        }

    external_dom_cap_used = float(max_dominant_share)
    if (
        enable_recent_adaptive_dominant_cap
        and str(external_primary.get("mode", "")) == "recent"
        and float(external_primary.get("accuracy", 0.0)) >= float(recent_adaptive_min_accuracy)
        and float(external_primary.get("mixed_bull_capture", 0.0)) >= float(recent_adaptive_min_bull_capture)
    ):
        external_dom_cap_used = max(float(max_dominant_share), float(recent_adaptive_cap))

    gate_eval = {
        "internal_gate": {
            "n_gate": wf_n >= min_n,
            "accuracy_gate": wf_acc >= min_accuracy,
            "margin_gate": wf_margin >= min_margin,
            "dominant_share_gate": wf_dom <= max_dominant_share,
            "internal_pass": bool(wf["biblical_only_path"]["gates"]["biblical_lane_candidate_ok"]),
        },
        "internal_equivalent_n_gate": {
            "available": bool(promo_internal),
            "candidate": promo_internal,
            "n_gate": bool(promo_internal and promo_internal["n_samples"] >= min_n),
            "accuracy_gate": bool(promo_internal and promo_internal["accuracy"] >= min_accuracy),
            "margin_gate": bool(promo_internal and promo_internal["margin_vs_random"] >= min_margin),
            "dominant_share_gate": bool(promo_internal and promo_internal["dominant_share"] <= max_dominant_share),
        },
        "external_reality_gate": {
            "mode": external_primary["mode"],
            "n_gate": external_primary["n_samples"] >= min_n,
            "accuracy_gate": external_primary["accuracy"] >= min_accuracy,
            "margin_gate": external_primary["margin_vs_random"] >= min_margin,
            "dominant_share_gate": external_primary["dominant_share"] <= external_dom_cap_used,
            "dominant_share_cap_used": round(external_dom_cap_used, 6),
            "external_reality_pass": bool(external_primary["external_reality_pass"]),
            "active_metrics": external_primary,
        },
        "external_reality_equivalent_n_gate": {
            "candidate_count": len(eq_candidates),
            "best_candidate": eq_best,
            "n_gate": bool(eq_best and eq_best["n_samples"] >= min_n),
            "accuracy_gate": bool(eq_best and eq_best["accuracy"] >= min_accuracy),
            "margin_gate": bool(eq_best and eq_best["margin_vs_random"] >= min_margin),
            "dominant_share_gate": bool(
                eq_best and (eq_best["dominant_share"] is None or eq_best["dominant_share"] <= max_dominant_share)
            ),
        },
    }

    blockers = []
    internal_n_ok = gate_eval["internal_gate"]["n_gate"] or gate_eval["internal_equivalent_n_gate"]["n_gate"]
    internal_dom_ok = gate_eval["internal_gate"]["dominant_share_gate"] or gate_eval["internal_equivalent_n_gate"]["dominant_share_gate"]
    if not internal_n_ok:
        blockers.append("internal_n_shortage")
    if not internal_dom_ok:
        blockers.append("internal_class_bias")
    if not gate_eval["external_reality_gate"]["external_reality_pass"]:
        blockers.append("external_reality_not_passed")
    if not gate_eval["external_reality_gate"]["n_gate"]:
        blockers.append("external_recent_n_shortage")
    if not gate_eval["external_reality_gate"]["dominant_share_gate"]:
        blockers.append("external_recent_class_bias")
    if not gate_eval["external_reality_equivalent_n_gate"]["accuracy_gate"]:
        blockers.append("equivalent_n_accuracy_below_target")

    policy_simulation = {
        "why_blocked": blockers,
        "internal": {
            "active_mode": "internal_equivalent_n" if gate_eval["internal_equivalent_n_gate"]["available"] else "internal_recent",
            "recent": {
                "accuracy": wf_acc,
                "margin_vs_random": wf_margin,
                "dominant_share": wf_dom,
                "n_samples": wf_n,
                "gates": gate_eval["internal_gate"],
            },
            "equivalent_n": gate_eval["internal_equivalent_n_gate"]["candidate"],
        },
        "external": {
            "active_mode": gate_eval["external_reality_gate"]["mode"],
            "active_metrics": gate_eval["external_reality_gate"]["active_metrics"],
            "active_gates": {
                "n_gate": gate_eval["external_reality_gate"]["n_gate"],
                "accuracy_gate": gate_eval["external_reality_gate"]["accuracy_gate"],
                "margin_gate": gate_eval["external_reality_gate"]["margin_gate"],
                "dominant_share_gate": gate_eval["external_reality_gate"]["dominant_share_gate"],
                "external_reality_pass": gate_eval["external_reality_gate"]["external_reality_pass"],
                "dominant_share_cap_used": gate_eval["external_reality_gate"]["dominant_share_cap_used"],
            },
            "counterfactual": {
                "recent_mode": {
                    "n_gate": bool(ext_recent["n_samples"] >= min_n),
                    "accuracy_gate": bool(ext_recent["accuracy"] >= min_accuracy),
                    "margin_gate": bool(ext_recent["margin_vs_random"] >= min_margin),
                    "dominant_share_gate": bool(ext_recent["dominant_share"] <= external_dom_cap_used),
                    "external_reality_pass": bool(ext_recent["external_reality_pass"]),
                    "dominant_share": float(ext_recent["dominant_share"]),
                    "dominant_share_cap_used": round(external_dom_cap_used, 6),
                    "accuracy": float(ext_recent["accuracy"]),
                    "n_samples": int(ext_recent["n_samples"]),
                },
                "equivalent_n_best": gate_eval["external_reality_equivalent_n_gate"]["best_candidate"],
                "equivalent_n_gate": {
                    "n_gate": gate_eval["external_reality_equivalent_n_gate"]["n_gate"],
                    "accuracy_gate": gate_eval["external_reality_equivalent_n_gate"]["accuracy_gate"],
                    "margin_gate": gate_eval["external_reality_equivalent_n_gate"]["margin_gate"],
                    "dominant_share_gate": gate_eval["external_reality_equivalent_n_gate"]["dominant_share_gate"],
                },
            },
        },
    }

    return {
        "schema": "kospi_biblical_single_lane_commercial_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "wf_json": str(wf_json.resolve()),
            "lock_json": str(lock_json.resolve()),
            "stability_json": str(stability_json.resolve()),
            "promotion_json": str(promotion_json.resolve()),
        },
        "targets": {
            "min_n": min_n,
            "min_accuracy": min_accuracy,
            "min_margin_vs_random": min_margin,
            "max_dominant_share": max_dominant_share,
            "recent_adaptive_dominant_cap": {
                "enabled": bool(enable_recent_adaptive_dominant_cap),
                "cap": float(recent_adaptive_cap),
                "min_accuracy": float(recent_adaptive_min_accuracy),
                "min_bull_capture": float(recent_adaptive_min_bull_capture),
            },
        },
        "current_metrics": {
            "internal": {
                "accuracy": wf_acc,
                "n_samples": wf_n,
                "margin_vs_random": wf_margin,
                "dominant_share": wf_dom,
                "predicted_counts": wf_test["counts_predicted"],
            },
            "external_recent_locked": ext_recent,
            "internal_equivalent_n": promo_internal,
            "external_equivalent_n_best": eq_best,
            "external_active_for_gate": external_primary,
        },
        "gates": gate_eval,
        "policy_simulation": policy_simulation,
        "blockers": blockers,
        "stage": "research" if blockers else "precommercial_ready",
        "precommercial_ready": not blockers,
        "note": "Internal gate and external reality gate are reported separately by design.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="KOSPI biblical-only commercialization gate report")
    ap.add_argument("--wf-json", type=Path, default=WF_DEFAULT)
    ap.add_argument("--lock-json", type=Path, default=LOCK_DEFAULT)
    ap.add_argument("--stability-json", type=Path, default=STABILITY_DEFAULT)
    ap.add_argument("--promotion-json", type=Path, default=PROMOTION_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--min-n", type=int, default=36)
    ap.add_argument("--min-accuracy", type=float, default=0.42)
    ap.add_argument("--min-margin", type=float, default=0.05)
    ap.add_argument("--max-dominant-share", type=float, default=0.70)
    ap.add_argument("--disable-recent-adaptive-dominant-cap", action="store_true")
    ap.add_argument("--recent-adaptive-cap", type=float, default=0.74)
    ap.add_argument("--recent-adaptive-min-accuracy", type=float, default=0.50)
    ap.add_argument("--recent-adaptive-min-bull-capture", type=float, default=0.15)
    ap.add_argument("--streak-required", type=int, default=3)
    ap.add_argument("--streak-min-spacing-hours", type=float, default=24.0)
    ap.add_argument("--log-jsonl", type=Path, default=LOG_DEFAULT)
    args = ap.parse_args()

    report = build_report(
        wf_json=args.wf_json,
        lock_json=args.lock_json,
        stability_json=args.stability_json,
        promotion_json=args.promotion_json,
        min_n=args.min_n,
        min_accuracy=args.min_accuracy,
        min_margin=args.min_margin,
        max_dominant_share=args.max_dominant_share,
        enable_recent_adaptive_dominant_cap=not bool(args.disable_recent_adaptive_dominant_cap),
        recent_adaptive_cap=args.recent_adaptive_cap,
        recent_adaptive_min_accuracy=args.recent_adaptive_min_accuracy,
        recent_adaptive_min_bull_capture=args.recent_adaptive_min_bull_capture,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Append compact history log for stability streak checks.
    args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)
    log_row = {
        "ts_utc": report["generated_at_utc"],
        "precommercial_ready": bool(report["precommercial_ready"]),
        "stage": report["stage"],
        "blockers": report["blockers"],
    }
    with args.log_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_row, ensure_ascii=False) + "\n")

    # Compute streak from tail (including this run).
    streak = 0
    spacing_hours = max(float(args.streak_min_spacing_hours), 0.0)
    latest_ts = datetime.fromisoformat(report["generated_at_utc"].replace("Z", "+00:00"))
    accepted_ts: datetime | None = None
    try:
        lines = args.log_jsonl.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            row = json.loads(line)
            if bool(row.get("precommercial_ready", False)):
                ts_raw = str(row.get("ts_utc", ""))
                try:
                    ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                except Exception:
                    break
                if accepted_ts is None:
                    # First accepted row is always this latest entry.
                    accepted_ts = ts
                    streak += 1
                    continue
                delta_h = (accepted_ts - ts).total_seconds() / 3600.0
                if delta_h >= spacing_hours:
                    accepted_ts = ts
                    streak += 1
                    continue
                # Same-day/too-close reruns do not increase streak, keep scanning.
                continue
            break
    except Exception:
        streak = 1 if report["precommercial_ready"] else 0

    report["stability"] = {
        "log_jsonl": str(args.log_jsonl.resolve()),
        "streak_required": args.streak_required,
        "streak_min_spacing_hours": spacing_hours,
        "current_ready_streak": streak,
        "stability_go": bool(report["precommercial_ready"] and streak >= args.streak_required),
        "latest_ts_utc": latest_ts.isoformat().replace("+00:00", "Z"),
    }
    report["stage"] = "commercial_candidate_stable" if report["stability"]["stability_go"] else report["stage"]
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out.resolve()),
                "stage": report["stage"],
                "precommercial_ready": report["precommercial_ready"],
                "blockers": report["blockers"],
                "ready_streak": report["stability"]["current_ready_streak"],
                "stability_go": report["stability"]["stability_go"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
