#!/usr/bin/env python3
"""
Deterministic watchdog: general prophecy holdout evolution artifacts + B-track hit-rate eval freshness.

Optional: append hit-rate observations to a JSONL tail (deduped by eval generated_at_utc),
then streak guard (last N samples all below threshold) and/or EMA floor guard.

Exit 0 if all checks pass; exit 1 if any check fails (caller may use -AllowNonZero in bundle).
B-track / general prophecy rails are observation-only; no auto-apply.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _rel_to_workspace(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _parse_utc(s: str) -> datetime:
    s = (s or "").strip()
    if not s:
        raise ValueError("empty timestamp")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _tail_jsonl_records(path: Path, *, max_lines: int = 400) -> list[dict]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()][-max_lines:]
    out: list[dict] = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def _append_hit_rate_tail(
    path: Path,
    *,
    eval_generated_at: str,
    hit_rate: float,
    recorded_at_utc: str,
    skip_if_duplicate: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if skip_if_duplicate and path.is_file():
        recs = _tail_jsonl_records(path, max_lines=8)
        if recs and recs[-1].get("sampled_from_eval_generated_at") == eval_generated_at:
            return
    row = {
        "schema": "prophecy_watchdog_hit_rate_tail_v1",
        "sampled_from_eval_generated_at": eval_generated_at,
        "hit_rate": float(hit_rate),
        "recorded_at_utc": recorded_at_utc,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _ema(values: list[float], alpha: float) -> float:
    if not values:
        return float("nan")
    e = float(values[0])
    for v in values[1:]:
        e = alpha * float(v) + (1.0 - alpha) * e
    return e


def main() -> int:
    p = argparse.ArgumentParser(description="Prophecy evolution + B-track eval staleness watchdog (Fact-Lock).")
    p.add_argument("--workspace-root", type=Path, required=True)
    p.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Default: <workspace>/reports/prophecy_evolution_watchdog_latest.json",
    )
    p.add_argument("--max-ablation-age-hours", type=float, default=96.0)
    p.add_argument("--max-hit-rate-age-hours", type=float, default=96.0)
    p.add_argument(
        "--allow-missing-ablation",
        action="store_true",
        help="If ablation JSON is missing, emit ok=false but exit 0 (bundle soft probe).",
    )
    p.add_argument(
        "--allow-missing-hit-rate",
        action="store_true",
        help="If hit-rate eval JSON is missing, skip that check (exit 0 for that check).",
    )
    p.add_argument(
        "--hit-rate-tail-jsonl",
        type=Path,
        default=None,
        help="Default: <workspace>/reports/prophecy_evolution_watchdog_hit_rate_tail_v1.jsonl",
    )
    p.add_argument(
        "--no-append-hit-rate-tail",
        action="store_true",
        help="Do not append the current eval hit-rate to the JSONL tail.",
    )
    p.add_argument(
        "--hit-rate-streak-count",
        type=int,
        default=0,
        help="If >0, fail when the last N tail observations (after append) are all strictly below --hit-rate-streak-below.",
    )
    p.add_argument("--hit-rate-streak-below", type=float, default=0.40)
    p.add_argument(
        "--hit-rate-ema-min",
        type=float,
        default=None,
        help="If set, fail when EMA(hit_rate tail, last --hit-rate-ema-max-lines) is strictly below this value.",
    )
    p.add_argument("--hit-rate-ema-alpha", type=float, default=0.25)
    p.add_argument("--hit-rate-ema-max-lines", type=int, default=48)
    args = p.parse_args()

    root: Path = args.workspace_root.resolve()
    out = args.out_json
    if out is None:
        out = root / "reports" / "prophecy_evolution_watchdog_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    tail_path = args.hit_rate_tail_jsonl
    if tail_path is None:
        tail_path = root / "reports" / "prophecy_evolution_watchdog_hit_rate_tail_v1.jsonl"

    now = datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    checks: list[dict] = []

    ablation_path = root / "docs/final/artifacts/general_prophecy_holdout_evolution_ablation_latest.json"
    ablation = _read_json(ablation_path)
    if ablation is None:
        checks.append(
            {
                "id": "general_prophecy_ablation_present",
                "ok": bool(args.allow_missing_ablation),
                "path": _rel_to_workspace(ablation_path, root),
                "age_hours": None,
                "max_hours": args.max_ablation_age_hours,
                "detail": "missing_file",
            }
        )
    else:
        try:
            gen = _parse_utc(str(ablation.get("generated_at_utc", "")))
            age_h = (now - gen).total_seconds() / 3600.0
            ok = age_h <= float(args.max_ablation_age_hours)
            checks.append(
                {
                    "id": "general_prophecy_ablation_fresh",
                    "ok": ok,
                    "path": "docs/final/artifacts/general_prophecy_holdout_evolution_ablation_latest.json",
                    "age_hours": round(age_h, 4),
                    "max_hours": args.max_ablation_age_hours,
                    "generated_at_utc": ablation.get("generated_at_utc"),
                }
            )
        except Exception as e:  # noqa: BLE001
            checks.append(
                {
                    "id": "general_prophecy_ablation_parse",
                    "ok": False,
                    "path": "docs/final/artifacts/general_prophecy_holdout_evolution_ablation_latest.json",
                    "detail": f"parse_error:{e}",
                }
            )

    candidates_path = root / "docs/final/artifacts/general_prophecy_holdout_evolution_candidates_latest.json"
    cand = _read_json(candidates_path)
    if cand is not None:
        try:
            gen = _parse_utc(str(cand.get("generated_at_utc", "")))
            age_h = (now - gen).total_seconds() / 3600.0
            ok = age_h <= float(args.max_ablation_age_hours)
            checks.append(
                {
                    "id": "general_prophecy_candidates_fresh",
                    "ok": ok,
                    "path": "docs/final/artifacts/general_prophecy_holdout_evolution_candidates_latest.json",
                    "age_hours": round(age_h, 4),
                    "max_hours": args.max_ablation_age_hours,
                    "generated_at_utc": cand.get("generated_at_utc"),
                }
            )
        except Exception as e:  # noqa: BLE001
            checks.append(
                {
                    "id": "general_prophecy_candidates_parse",
                    "ok": False,
                    "path": "docs/final/artifacts/general_prophecy_holdout_evolution_candidates_latest.json",
                    "detail": f"parse_error:{e}",
                }
            )

    hit_path = root / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
    hit = _read_json(hit_path)
    current_hit_rate: float | None = None
    current_eval_gen: str | None = None

    if hit is None:
        if not args.allow_missing_hit_rate:
            checks.append(
                {
                    "id": "btrack_hit_rate_eval_present",
                    "ok": False,
                    "path": _rel_to_workspace(hit_path, root),
                    "detail": "missing_file",
                }
            )
        else:
            checks.append(
                {
                    "id": "btrack_hit_rate_eval_present",
                    "ok": True,
                    "path": "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
                    "detail": "skipped_allow_missing",
                }
            )
    else:
        try:
            gen = _parse_utc(str(hit.get("generated_at_utc", "")))
            age_h = (now - gen).total_seconds() / 3600.0
            ok = age_h <= float(args.max_hit_rate_age_hours)
            checks.append(
                {
                    "id": "btrack_hit_rate_eval_fresh",
                    "ok": ok,
                    "path": "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
                    "age_hours": round(age_h, 4),
                    "max_hours": args.max_hit_rate_age_hours,
                    "generated_at_utc": hit.get("generated_at_utc"),
                }
            )
            metrics = hit.get("metrics") or {}
            if "price_directional_hit_rate" in metrics:
                current_hit_rate = float(metrics["price_directional_hit_rate"])
                current_eval_gen = str(hit.get("generated_at_utc") or "")
        except Exception as e:  # noqa: BLE001
            checks.append(
                {
                    "id": "btrack_hit_rate_eval_parse",
                    "ok": False,
                    "path": "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
                    "detail": f"parse_error:{e}",
                }
            )

    if (
        current_hit_rate is not None
        and current_eval_gen
        and not args.no_append_hit_rate_tail
        and (args.hit_rate_streak_count > 0 or args.hit_rate_ema_min is not None)
    ):
        _append_hit_rate_tail(
            tail_path,
            eval_generated_at=current_eval_gen,
            hit_rate=current_hit_rate,
            recorded_at_utc=now_iso,
            skip_if_duplicate=True,
        )

    streak_n = int(args.hit_rate_streak_count)
    if streak_n > 0 and current_hit_rate is not None:
        recs = _tail_jsonl_records(tail_path, max_lines=max(400, streak_n * 20))
        rates = [float(r["hit_rate"]) for r in recs if isinstance(r.get("hit_rate"), (int, float))]
        if len(rates) < streak_n:
            checks.append(
                {
                    "id": "btrack_hit_rate_streak_guard",
                    "ok": True,
                    "detail": "insufficient_tail_history",
                    "streak_count": streak_n,
                    "streak_below": args.hit_rate_streak_below,
                    "tail_samples": len(rates),
                }
            )
        else:
            window = rates[-streak_n:]
            below_thr = float(args.hit_rate_streak_below)
            ok = not all(x <= below_thr for x in window)
            checks.append(
                {
                    "id": "btrack_hit_rate_streak_guard",
                    "ok": ok,
                    "streak_count": streak_n,
                    "streak_below": below_thr,
                    "window_hit_rates": [round(x, 6) for x in window],
                    "tail_path": _rel_to_workspace(tail_path, root),
                }
            )

    if args.hit_rate_ema_min is not None:
        recs = _tail_jsonl_records(tail_path, max_lines=max(400, int(args.hit_rate_ema_max_lines) * 2))
        rates = [float(r["hit_rate"]) for r in recs if isinstance(r.get("hit_rate"), (int, float))]
        cap = max(3, int(args.hit_rate_ema_max_lines))
        series = rates[-cap:]
        if len(series) < 3:
            checks.append(
                {
                    "id": "btrack_hit_rate_ema_guard",
                    "ok": True,
                    "detail": "insufficient_tail_history",
                    "ema_min": args.hit_rate_ema_min,
                    "tail_samples": len(series),
                }
            )
        else:
            ema_val = _ema(series, float(args.hit_rate_ema_alpha))
            floor = float(args.hit_rate_ema_min)
            ok = not (ema_val < floor)
            checks.append(
                {
                    "id": "btrack_hit_rate_ema_guard",
                    "ok": ok,
                    "ema": round(ema_val, 6),
                    "ema_alpha": args.hit_rate_ema_alpha,
                    "ema_min": floor,
                    "series_len": len(series),
                    "tail_path": _rel_to_workspace(tail_path, root),
                }
            )

    overall_ok = all(bool(c.get("ok")) for c in checks)
    payload = {
        "schema": "prophecy_evolution_watchdog_v1",
        "checked_at_utc": now_iso,
        "workspace_root": str(root),
        "overall_ok": overall_ok,
        "checks": checks,
        "hit_rate_tail_jsonl": _rel_to_workspace(tail_path, root),
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
