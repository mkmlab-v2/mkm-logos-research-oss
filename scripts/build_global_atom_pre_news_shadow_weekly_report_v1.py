#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_stage_thresholds(raw: str) -> dict[str, int]:
    out: dict[str, int] = {}
    if not raw.strip():
        return out
    for part in raw.split(","):
        token = part.strip()
        if not token or ":" not in token:
            continue
        key, val = token.split(":", 1)
        stage = key.strip()
        if not stage:
            continue
        try:
            n = int(val.strip())
        except Exception:
            continue
        if n >= 1:
            out[stage] = n
    return out


def load_threshold_policy(path: Path) -> tuple[int | None, dict[str, int]]:
    if not path.is_file():
        return None, {}
    try:
        obj = read_json(path)
    except Exception:
        return None, {}
    default_min: int | None = None
    raw_default = obj.get("default_min_holdout_cases_per_stage")
    if isinstance(raw_default, int) and raw_default >= 1:
        default_min = raw_default
    stage_map: dict[str, int] = {}
    raw_stage = obj.get("stage_min_holdout_cases")
    if isinstance(raw_stage, dict):
        for k, v in raw_stage.items():
            if isinstance(v, int) and v >= 1:
                stage_map[str(k)] = v
    return default_min, stage_map


def policy_metadata(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = read_json(path)
    except Exception:
        return {}
    keys = (
        "schema",
        "policy_version",
        "approved_by",
        "approved_by_1",
        "approved_by_2",
        "effective_from_utc",
        "updated_at_utc",
    )
    return {k: obj.get(k) for k in keys if k in obj}


def policy_fingerprint(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        obj = read_json(path)
    except Exception:
        return ""
    canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def read_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = read_json(path)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def write_state(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def dominant_stage(rows: list[dict[str, Any]]) -> str | None:
    c: Counter[str] = Counter()
    for r in rows:
        stage = str(r.get("primary_top_stage", "") or "").strip()
        if stage:
            c[stage] += 1
    return c.most_common(1)[0][0] if c else None


def count_alerts_in_window(path: Path, cutoff: datetime) -> int:
    if not path.is_file():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        dt = parse_iso(str(row.get("generated_at_utc", "") or ""))
        if dt is None or dt < cutoff:
            continue
        if bool(row.get("has_alert", False)):
            n += 1
    return n


def holdout_stage_counts(path: Path) -> Counter[str]:
    out: Counter[str] = Counter()
    if not path.is_file():
        return out
    try:
        obj = read_json(path)
    except Exception:
        return out
    summary = obj.get("summary") if isinstance(obj.get("summary"), dict) else {}
    if isinstance(summary, dict):
        c = summary.get("holdout_top_stage_counts")
        if isinstance(c, dict):
            for k, v in c.items():
                try:
                    out[str(k)] += int(v)
                except Exception:
                    continue
            if out:
                return out
    for c in obj.get("cases", []) if isinstance(obj.get("cases"), list) else []:
        if not isinstance(c, dict):
            continue
        top = c.get("top_resonance")
        if isinstance(top, dict):
            stage = str(top.get("stage", "") or "").strip()
            if stage:
                out[stage] += 1
    return out


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_holdout_dataset_lock(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = read_json(path)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build weekly summary for pre-news shadow projection logs.")
    ap.add_argument("--log-jsonl", default="reports/pre_news_shadow_projection_log.jsonl")
    ap.add_argument("--alert-log-jsonl", default="reports/pre_news_shadow_task_health_alert_log.jsonl")
    ap.add_argument("--holdout-replay-json", default="docs/final/artifacts/global_atom_news_network_holdout_replay_latest.json")
    ap.add_argument("--holdout-dataset-lock-json", default="docs/final/artifacts/global_atom_news_holdout_dataset_lock_manifest_v1.json")
    ap.add_argument("--enforce-holdout-dataset-lock", action="store_true")
    ap.add_argument("--min-holdout-cases-per-stage", type=int, default=2)
    ap.add_argument("--stage-threshold-policy-json", default="")
    ap.add_argument("--policy-change-log-jsonl", default="reports/pre_news_shadow_stage_threshold_policy_change_log.jsonl")
    ap.add_argument("--policy-state-json", default="docs/final/artifacts/pre_news_shadow_stage_threshold_policy_state_latest.json")
    ap.add_argument("--enforce-policy-effective-from", action="store_true")
    ap.add_argument(
        "--stage-min-holdout-cases",
        default="",
        help="Comma-separated per-stage thresholds, e.g. full_canon:5,prophets:3,gospels:3",
    )
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--out-json", default="docs/final/artifacts/pre_news_shadow_weekly_report_latest.json")
    args = ap.parse_args()

    log_path = resolve(args.log_jsonl)
    alert_log_path = resolve(args.alert_log_jsonl)
    holdout_path = resolve(args.holdout_replay_json)
    holdout_lock_path = resolve(args.holdout_dataset_lock_json)
    policy_path = resolve(args.stage_threshold_policy_json) if str(args.stage_threshold_policy_json or "").strip() else None
    policy_log_path = resolve(args.policy_change_log_jsonl)
    policy_state_path = resolve(args.policy_state_json)
    out_path = resolve(args.out_json)
    if not log_path.is_file():
        raise SystemExit(f"missing log jsonl: {log_path}")

    cutoff = now() - timedelta(days=max(1, args.window_days))
    prev_cutoff = cutoff - timedelta(days=max(1, args.window_days))
    all_rows: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        all_rows.append(row)
        dt = parse_iso(str(row.get("generated_at_utc", "") or ""))
        if dt is None or dt < cutoff:
            continue
        kept.append(row)

    prev_rows: list[dict[str, Any]] = []
    for row in all_rows:
        dt = parse_iso(str(row.get("generated_at_utc", "") or ""))
        if dt is None:
            continue
        if prev_cutoff <= dt < cutoff:
            prev_rows.append(row)

    top_counter: Counter[str] = Counter()
    total_rows = 0
    latest_projection_path: Path | None = None
    if kept:
        cand = str(kept[-1].get("output_json", "") or "").strip()
        if cand:
            latest_projection_path = Path(cand)
    if latest_projection_path is not None and latest_projection_path.is_file():
        proj = read_json(latest_projection_path)
        for p in proj.get("projections", []) if isinstance(proj.get("projections"), list) else []:
            if not isinstance(p, dict):
                continue
            top = p.get("top_resonance")
            if isinstance(top, dict):
                stage = str(top.get("stage", "") or "").strip()
                if stage:
                    top_counter[stage] += 1
            total_rows += 1

    most_common = [{"stage": k, "count": v} for k, v in top_counter.most_common(5)]
    holdout_replay_obj = read_json(holdout_path) if holdout_path.is_file() else {}
    replay_input = holdout_replay_obj.get("input") if isinstance(holdout_replay_obj.get("input"), dict) else {}
    replay_dataset_path = resolve(str(replay_input.get("holdout_news_jsonl", "") or "")) if replay_input.get("holdout_news_jsonl") else None
    lock_obj = load_holdout_dataset_lock(holdout_lock_path)
    lock_sha = str(lock_obj.get("dataset_sha256", "") or "")
    actual_sha = sha256_file(replay_dataset_path) if replay_dataset_path is not None else ""
    holdout_dataset_lock_ok = bool(lock_sha and actual_sha and lock_sha == actual_sha)
    if args.enforce_holdout_dataset_lock and not holdout_dataset_lock_ok:
        # Degrade gate instead of hard-fail: keep observability while blocking promotion.
        most_common = [{"stage": r.get("stage"), "count": r.get("count")} for r in most_common]
    holdout_counts = holdout_stage_counts(holdout_path)
    default_threshold = max(1, int(args.min_holdout_cases_per_stage))
    per_stage_thresholds = parse_stage_thresholds(str(args.stage_min_holdout_cases or ""))
    policy_default = None
    policy_stage_map: dict[str, int] = {}
    if policy_path is not None:
        policy_default, policy_stage_map = load_threshold_policy(policy_path)
        meta = policy_metadata(policy_path)
        effective_raw = str(meta.get("effective_from_utc", "") or "").strip()
        effective_dt = parse_iso(effective_raw) if effective_raw else None
        if args.enforce_policy_effective_from and effective_raw and effective_dt is None:
            raise SystemExit(f"invalid effective_from_utc in policy: {effective_raw}")
        if args.enforce_policy_effective_from and effective_dt is not None and now() < effective_dt:
            raise SystemExit(f"policy not yet effective: {effective_raw}")
        if policy_default is not None:
            default_threshold = max(1, int(policy_default))
        per_stage_thresholds = dict(policy_stage_map)
        # CLI override remains highest priority for ad-hoc runs.
        per_stage_thresholds.update(parse_stage_thresholds(str(args.stage_min_holdout_cases or "")))
        fp = policy_fingerprint(policy_path)
        prev = read_state(policy_state_path)
        prev_fp = str(prev.get("policy_fingerprint_sha256", "") or "")
        changed = bool(fp and fp != prev_fp)
        if changed:
            append_jsonl(
                policy_log_path,
                {
                    "schema": "pre_news_shadow_stage_threshold_policy_change_log_v1",
                    "detected_at_utc": to_iso(now()),
                    "policy_path": str(policy_path),
                    "policy_fingerprint_sha256": fp,
                    "previous_policy_fingerprint_sha256": prev_fp or None,
                    "policy_version": meta.get("policy_version"),
                    "approved_by": meta.get("approved_by"),
                    "effective_from_utc": meta.get("effective_from_utc"),
                },
            )
        write_state(
            policy_state_path,
            {
                "schema": "pre_news_shadow_stage_threshold_policy_state_v1",
                "updated_at_utc": to_iso(now()),
                "policy_path": str(policy_path),
                "policy_fingerprint_sha256": fp,
                "policy_version": meta.get("policy_version"),
                "approved_by": meta.get("approved_by"),
                "approved_by_1": meta.get("approved_by_1"),
                "approved_by_2": meta.get("approved_by_2"),
                "effective_from_utc": meta.get("effective_from_utc"),
            },
        )
    else:
        meta = {}
    verified = set()
    for k, v in holdout_counts.items():
        need = int(per_stage_thresholds.get(k, default_threshold))
        if int(v) >= need:
            verified.add(k)
    promoted = [row for row in most_common if str(row.get("stage", "") or "") in verified]
    if args.enforce_holdout_dataset_lock and not holdout_dataset_lock_ok:
        promoted = []
    rejected = []
    for row in most_common:
        st = str(row.get("stage", "") or "")
        if st and (st not in verified or (args.enforce_holdout_dataset_lock and not holdout_dataset_lock_ok)):
            rejected.append(
                {
                    "stage": st,
                    "count": row.get("count"),
                    "holdout_count": int(holdout_counts.get(st, 0)),
                    "required_count": int(per_stage_thresholds.get(st, default_threshold)),
                    "reject_reason": (
                        "holdout_dataset_hash_mismatch"
                        if args.enforce_holdout_dataset_lock and not holdout_dataset_lock_ok
                        else (
                        "below_min_holdout_cases_per_stage"
                        if st in holdout_counts
                        else "not_in_holdout_verified_stages"
                        )
                    ),
                }
            )
    current_primary = dominant_stage(kept)
    prev_primary = dominant_stage(prev_rows)

    seq = [str(r.get("primary_top_stage", "") or "").strip() for r in kept]
    seq = [s for s in seq if s]
    transitions = 0
    if len(seq) >= 2:
        transitions = sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])
    top_stage_change_rate = (transitions / (len(seq) - 1)) if len(seq) >= 2 else 0.0
    top_stage_drift = bool(current_primary and prev_primary and current_primary != prev_primary)
    alert_count_7d = count_alerts_in_window(alert_log_path, cutoff)

    if alert_count_7d > 0:
        risk = f"HIGH: {alert_count_7d} health alert(s) detected in last {max(1, args.window_days)} days."
    elif top_stage_drift or top_stage_change_rate >= 0.5:
        risk = "MEDIUM: resonance stage is unstable (drift/change-rate elevated)."
    else:
        risk = "LOW: resonance stage is stable and no health alerts detected."

    report = {
        "schema": "pre_news_shadow_weekly_report_v1",
        "generated_at_utc": to_iso(now()),
        "window_days": max(1, args.window_days),
        "log_jsonl": str(log_path),
        "alert_log_jsonl": str(alert_log_path),
        "holdout_replay_json": str(holdout_path),
        "holdout_dataset_lock_json": str(holdout_lock_path),
        "stage_threshold_policy_json": str(policy_path) if policy_path is not None else None,
        "stage_threshold_policy_change_log_jsonl": str(policy_log_path) if policy_path is not None else None,
        "stage_threshold_policy_state_json": str(policy_state_path) if policy_path is not None else None,
        "stage_threshold_policy_meta": meta,
        "runs_in_window": len(kept),
        "latest_projection_json": str(latest_projection_path) if latest_projection_path is not None else None,
        "latest_projection_rows": total_rows,
        "top_resonance_stage_counts": most_common,
        "promoted_stage_counts": promoted,
        "rejected_stage_counts": rejected,
        "metrics": {
            "top_stage_change_rate": round(top_stage_change_rate, 4),
            "top_stage_current_primary": current_primary,
            "top_stage_previous_primary": prev_primary,
            "top_stage_drift": top_stage_drift,
            "health_alert_count_7d": alert_count_7d,
            "holdout_verified_stage_count": len(verified),
            "holdout_min_cases_per_stage": default_threshold,
            "promoted_stage_count": len(promoted),
            "rejected_stage_count": len(rejected),
        },
        "promotion_gate": {
            "enabled": bool(not (args.enforce_holdout_dataset_lock and not holdout_dataset_lock_ok)),
            "rule": "only stages with holdout top_resonance count >= required threshold (stage override or default) are promoted",
            "holdout_dataset_lock_enforced": bool(args.enforce_holdout_dataset_lock),
            "holdout_dataset_lock_ok": holdout_dataset_lock_ok,
            "holdout_dataset_expected_sha256": lock_sha or None,
            "holdout_dataset_actual_sha256": actual_sha or None,
            "min_holdout_cases_per_stage": default_threshold,
            "stage_min_holdout_cases": per_stage_thresholds,
            "holdout_top_stage_counts": dict(holdout_counts),
            "holdout_verified_stages": sorted(verified),
        },
        "risk_summary": risk,
        "research_only": True,
        "note": "Weekly monitoring summary for shadow-only pre-news projection.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

