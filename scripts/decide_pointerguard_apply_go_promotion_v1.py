#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DAILY_REPORT_DEFAULT = ART / "pointer_hash_snapping_router_shadow_daily_report_latest.json"
ALERT_DEFAULT = ART / "pointer_hash_snapping_router_shadow_alert_latest.json"
LOG_DEFAULT = REPORTS / "pointer_hash_snapping_router_shadow_log_v1.jsonl"
FOLDER_POLICY_DEFAULT = ART / "pointerguard_folder_policy_latest.json"
SNAPSHOT_DEFAULT = ART / "pointer_hash_snapping_router_shadow_latest.json"
OUT_DEFAULT = ART / "pointerguard_apply_go_promotion_decision_latest.json"
READINESS_DEFAULT = ART / "pointerguard_ops_readiness_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _select_profile(policy_doc: dict[str, Any], target_path: str) -> dict[str, Any]:
    normalized = target_path.replace("\\", "/").lstrip("./")
    profiles = policy_doc.get("promotion_profiles", [])
    if not isinstance(profiles, list):
        return {}
    best: dict[str, Any] = {}
    best_specificity = -1
    for p in profiles:
        if not isinstance(p, dict):
            continue
        patterns = p.get("match_patterns", [])
        if not isinstance(patterns, list):
            continue
        for patt in patterns:
            sp = str(patt).strip()
            if not sp:
                continue
            if fnmatch.fnmatch(normalized, sp):
                if len(sp) > best_specificity:
                    best = p
                    best_specificity = len(sp)
    return best


def _filter_logs_for_profile(logs: list[dict[str, Any]], profile: dict[str, Any], target_path: str) -> list[dict[str, Any]]:
    patterns = profile.get("match_patterns", []) if isinstance(profile, dict) else []
    if not isinstance(patterns, list) or not patterns:
        return logs
    out: list[dict[str, Any]] = []
    for row in logs:
        if not isinstance(row, dict):
            continue
        tp = str(row.get("target_path", "")).replace("\\", "/").lstrip("./")
        if not tp:
            continue
        if any(fnmatch.fnmatch(tp, str(p)) for p in patterns):
            out.append(row)
    return out


def _point_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    rows = snapshot.get("rows", [])
    summary = snapshot.get("summary", {})
    if not isinstance(rows, list):
        rows = []
    target_path = str(snapshot.get("inputs", {}).get("target_path", ""))
    return {
        "input_count": int(snapshot.get("inputs", {}).get("input_count", len(rows))),
        "pointer_candidate_ok_count": int(summary.get("pointer_candidate_ok_count", 0)),
        "selected_pointer_count": int(summary.get("selected_pointer_count", 0)),
        "selected_track_a_count": int(summary.get("selected_track_a_count", 0)),
        "snap_event_count": int(sum(len(r.get("snap_events", [])) for r in rows if isinstance(r, dict))),
        "oov_unresolved_token_count": int(sum(len(r.get("unresolved_tokens", [])) for r in rows if isinstance(r, dict))),
        "path_policy_counts": {
            "apply": int(sum(1 for r in rows if isinstance(r, dict) and str(r.get("path_policy")) == "apply")),
            "caution": int(sum(1 for r in rows if isinstance(r, dict) and str(r.get("path_policy")) == "caution")),
            "forbid": int(sum(1 for r in rows if isinstance(r, dict) and str(r.get("path_policy")) == "forbid")),
            "unknown": int(sum(1 for r in rows if isinstance(r, dict) and str(r.get("path_policy")) not in {"apply", "caution", "forbid"})),
        },
        "path_policy_unresolved_token_counts": {
            "apply": int(
                sum(
                    len(r.get("unresolved_tokens", []))
                    for r in rows
                    if isinstance(r, dict) and str(r.get("path_policy")) == "apply"
                )
            ),
            "caution": int(
                sum(
                    len(r.get("unresolved_tokens", []))
                    for r in rows
                    if isinstance(r, dict) and str(r.get("path_policy")) == "caution"
                )
            ),
            "forbid": int(
                sum(
                    len(r.get("unresolved_tokens", []))
                    for r in rows
                    if isinstance(r, dict) and str(r.get("path_policy")) == "forbid"
                )
            ),
            "unknown": int(
                sum(
                    len(r.get("unresolved_tokens", []))
                    for r in rows
                    if isinstance(r, dict) and str(r.get("path_policy")) not in {"apply", "caution", "forbid"}
                )
            ),
        },
        "target_path": target_path,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daily-report", type=Path, default=DAILY_REPORT_DEFAULT)
    ap.add_argument("--alert-json", type=Path, default=ALERT_DEFAULT)
    ap.add_argument("--shadow-log-jsonl", type=Path, default=LOG_DEFAULT)
    ap.add_argument("--folder-policy-json", type=Path, default=FOLDER_POLICY_DEFAULT)
    ap.add_argument("--latest-snapshot-json", type=Path, default=SNAPSHOT_DEFAULT)
    ap.add_argument("--prefer-latest-snapshot", action="store_true")
    ap.add_argument("--target-path", type=str, default="docs/final/artifacts/pointer_router_chain_probe.json")
    ap.add_argument("--consecutive-samples", type=int, default=3)
    ap.add_argument("--apply-row-ratio-min", type=float, default=0.30)
    ap.add_argument("--apply-unresolved-max", type=float, default=2.0)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--readiness-json", type=Path, default=READINESS_DEFAULT)
    args = ap.parse_args()

    report_path = args.daily_report if args.daily_report.is_absolute() else ROOT / args.daily_report
    alert_path = args.alert_json if args.alert_json.is_absolute() else ROOT / args.alert_json
    log_path = args.shadow_log_jsonl if args.shadow_log_jsonl.is_absolute() else ROOT / args.shadow_log_jsonl
    policy_path = args.folder_policy_json if args.folder_policy_json.is_absolute() else ROOT / args.folder_policy_json
    snapshot_path = args.latest_snapshot_json if args.latest_snapshot_json.is_absolute() else ROOT / args.latest_snapshot_json
    readiness_path = args.readiness_json if args.readiness_json.is_absolute() else ROOT / args.readiness_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    rep = _read_json(report_path)
    alert = _read_json(alert_path)
    logs = _read_jsonl(log_path)
    policy_doc = _read_json(policy_path)
    readiness_all_ok = False
    if readiness_path.exists():
        try:
            readiness_all_ok = bool(_read_json(readiness_path).get("all_ok", False))
        except Exception:
            readiness_all_ok = False

    profile = _select_profile(policy_doc, args.target_path)
    logs = _filter_logs_for_profile(logs, profile, args.target_path)
    if args.prefer_latest_snapshot and snapshot_path.exists():
        snap = _read_json(snapshot_path)
        logs = [_point_from_snapshot(snap)]
    k = int(profile.get("consecutive_samples", args.consecutive_samples)) if profile else int(args.consecutive_samples)
    apply_row_ratio_min = (
        float(profile.get("apply_row_ratio_min", args.apply_row_ratio_min)) if profile else float(args.apply_row_ratio_min)
    )
    ramp_thresholds = []
    ramp_index = 0
    if profile and isinstance(profile.get("ramp_unresolved_thresholds"), list):
        ramp_thresholds = [float(x) for x in profile.get("ramp_unresolved_thresholds", [])]
        ramp_index = int(profile.get("ramp_current_index", 0))
        if ramp_thresholds:
            ramp_index = min(max(0, ramp_index), len(ramp_thresholds) - 1)
    apply_unresolved_max = (
        float(profile.get("apply_unresolved_max", args.apply_unresolved_max)) if profile else float(args.apply_unresolved_max)
    )
    if ramp_thresholds:
        apply_unresolved_max = float(ramp_thresholds[ramp_index])

    k = max(1, k)
    recent = logs[-k:] if len(logs) >= k else logs

    reasons: list[str] = []
    if bool(alert.get("should_alert", False)):
        reasons.append("active_shadow_alert")
    if not readiness_all_ok:
        reasons.append("blocked_by_ops_readiness")
    if profile and not bool(profile.get("go_promotion_enabled", False)):
        reasons.append("profile_go_promotion_disabled")

    if len(recent) < k and not args.prefer_latest_snapshot:
        reasons.append("insufficient_recent_samples")

    per_sample_checks: list[dict[str, Any]] = []
    for idx, row in enumerate(recent):
        total_inputs = float(row.get("input_count", 0.0))
        policy_counts = row.get("path_policy_counts", {})
        policy_unresolved = row.get("path_policy_unresolved_token_counts", {})
        apply_rows = float(policy_counts.get("apply", 0.0))
        apply_unresolved = float(policy_unresolved.get("apply", 0.0))
        apply_ratio = apply_rows / float(max(1.0, total_inputs))
        ok_ratio = apply_ratio >= apply_row_ratio_min
        ok_unresolved = apply_unresolved <= apply_unresolved_max
        per_sample_checks.append(
            {
                "sample_index_from_recent": idx,
                "input_count": total_inputs,
                "apply_ratio": apply_ratio,
                "apply_unresolved": apply_unresolved,
                "pass_apply_ratio": ok_ratio,
                "pass_apply_unresolved": ok_unresolved,
            }
        )
        if not ok_ratio:
            reasons.append("apply_ratio_below_threshold")
        if not ok_unresolved:
            reasons.append("apply_unresolved_above_threshold")

    ws = rep.get("window_stats", {})
    apply_ratio_window = float(ws.get("path_policy_avg_row_ratio", {}).get("apply", 0.0))
    apply_unresolved_window = float(ws.get("path_policy_avg_unresolved_per_run", {}).get("apply", 0.0))

    promote = len(reasons) == 0
    out_doc = {
        "schema": "pointerguard_apply_go_promotion_decision_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {
            "daily_report": str(report_path),
            "alert_json": str(alert_path),
            "shadow_log_jsonl": str(log_path),
            "folder_policy_json": str(policy_path),
            "target_path": args.target_path,
            "readiness_json": str(readiness_path),
            "readiness_all_ok": readiness_all_ok,
            "consecutive_samples": k,
            "apply_row_ratio_min": apply_row_ratio_min,
            "apply_unresolved_max": apply_unresolved_max,
            "profile_id": str(profile.get("profile_id", "default")) if profile else "default",
            "go_promotion_enabled": bool(profile.get("go_promotion_enabled", False)) if profile else True,
            "rollout_order": profile.get("rollout_order") if profile else None,
            "ramp_unresolved_thresholds": ramp_thresholds,
            "ramp_current_index": ramp_index if ramp_thresholds else None,
            "filtered_log_count": len(logs),
        },
        "window_stats": {
            "sample_count": int(ws.get("sample_count", 0)),
            "apply_row_ratio_avg": apply_ratio_window,
            "apply_unresolved_avg_per_run": apply_unresolved_window,
        },
        "recent_checks": per_sample_checks,
        "promote_apply_path_to_go": promote,
        "decision": "PROMOTE_APPLY_GO" if promote else "KEEP_SHADOW",
        "reasons": sorted(set(reasons)),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "promote_apply_path_to_go": promote,
                "decision": out_doc["decision"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
