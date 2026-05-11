#!/usr/bin/env python3
"""B-track: one-step Valence-Arousal EMA trajectory row (M20 EMA pattern extension).

Writes `reports/va_trajectory_log_latest.json` and updates optional state file for chained turns.
Advisory / research lane only — see CONSTITUTION §3.8.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "va_trajectory_log_latest.json"
DEFAULT_STATE = ROOT / "reports" / "lens_emotion_va_trajectory_state_latest.json"
DEFAULT_JSONL = ROOT / "reports" / "va_trajectory_log.jsonl"
DEFAULT_COOLDOWN_EVENT_OUT = ROOT / "reports" / "va_cooldown_event_log_latest.json"
DEFAULT_COOLDOWN_EVENT_JSONL = ROOT / "reports" / "va_cooldown_event_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _apply_ema(previous: float, target: float, alpha: float) -> float:
    a = max(0.0, min(1.0, float(alpha)))
    return (a * float(target)) + ((1.0 - a) * float(previous))


def _clip_va(v: float, a: float) -> tuple[float, float]:
    def _c(x: float) -> float:
        return max(-1.0, min(1.0, float(x)))

    return _c(v), _c(a)


def _target_va_from_chain(chain: dict[str, Any]) -> tuple[float, float]:
    m9 = dict(chain.get("melody_stage_m9") or {})
    snapshot = dict(m9.get("input_snapshot") or {})
    evo = dict(chain.get("emotion_va_overlay_v1") or {})
    v = float(snapshot.get("valence") if snapshot.get("valence") is not None else evo.get("valence") or 0.0)
    ar = float(snapshot.get("arousal") if snapshot.get("arousal") is not None else evo.get("arousal") or 0.0)
    return _clip_va(v, ar)


def build_trajectory_row(
    *,
    session_id: str,
    turn_index: int,
    target_valence: float,
    target_arousal: float,
    prev_state: dict[str, Any] | None,
    ema_alpha: float,
    sasang_base: str | None,
    status: str,
    note: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    alpha = max(0.0, min(1.0, float(ema_alpha)))
    prev_va = dict((prev_state or {}).get("current_va") or {})
    pv = float(prev_va.get("valence", 0.0))
    pa = float(prev_va.get("arousal", 0.0))
    pv, pa = _clip_va(pv, pa)
    tv, ta = _clip_va(target_valence, target_arousal)

    cv = round(_apply_ema(pv, tv, alpha), 6)
    ca = round(_apply_ema(pa, ta, alpha), 6)
    cv, ca = _clip_va(cv, ca)

    row = {
        "schema": "va_trajectory_log_v1",
        "hypothesis_class": "HYPO",
        "session_id": session_id,
        "turn_index": int(turn_index),
        "timestamp_utc": _utc_now(),
        "parameters": {
            "ema_alpha": float(alpha),
            **({"sasang_base": sasang_base} if sasang_base else {}),
        },
        "trajectory": {
            "previous_va": {"valence": pv, "arousal": pa},
            "target_va": {"valence": tv, "arousal": ta},
            "current_va": {"valence": cv, "arousal": ca},
        },
        "status": status,
        **({"note": note} if note else {}),
    }
    next_state = {
        "schema": "lens_emotion_va_trajectory_state_v1",
        "generated_at_utc": _utc_now(),
        "session_id": session_id,
        "last_turn_index": int(turn_index),
        "ema_alpha": float(alpha),
        "current_va": {"valence": cv, "arousal": ca},
    }
    return row, next_state


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _apply_cooldown(
    *,
    valence: float,
    arousal: float,
    high_arousal_cut: float,
    low_valence_cut: float,
    arousal_decay_step: float,
    valence_recovery_step: float,
) -> dict[str, Any]:
    before_v, before_a = _clip_va(valence, arousal)
    after_v, after_a = before_v, before_a
    reasons: list[str] = []
    if after_a > float(high_arousal_cut):
        after_a = max(0.0, after_a - max(0.0, float(arousal_decay_step)))
        reasons.append("high_arousal")
    if after_v < float(low_valence_cut):
        after_v = min(0.0, after_v + max(0.0, float(valence_recovery_step)))
        reasons.append("low_valence")
    after_v, after_a = _clip_va(after_v, after_a)
    return {
        "applied": len(reasons) > 0,
        "reasons": reasons,
        "before_va": {"valence": before_v, "arousal": before_a},
        "after_va": {"valence": after_v, "arousal": after_a},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-id", type=str, default="local_session_v1")
    ap.add_argument("--turn-index", type=int, default=0)
    ap.add_argument("--ema-alpha", type=float, default=0.4)
    ap.add_argument("--target-valence", type=float, default=None, help="Target VA from upstream (ignored if --chain-json supplies snapshot).")
    ap.add_argument("--target-arousal", type=float, default=None)
    ap.add_argument("--chain-json", type=Path, default=None, help="Optional lens-music chain doc; reads melody_stage_m9.input_snapshot VA.")
    ap.add_argument("--sasang-base", type=str, default=None)
    ap.add_argument("--status", type=str, default="TRACKING_ACTIVE")
    ap.add_argument("--note", type=str, default=None)
    ap.add_argument("--prev-state-json", type=Path, default=None, help="Defaults to --state-json path.")
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--jsonl-log", type=Path, nargs="?", const=DEFAULT_JSONL, default=None)
    ap.add_argument("--enable-cooldown", action="store_true")
    ap.add_argument("--cooldown-policy-id", type=str, default="va_cooldown_control_v1")
    ap.add_argument("--high-arousal-cut", type=float, default=0.9)
    ap.add_argument("--low-valence-cut", type=float, default=-0.9)
    ap.add_argument("--arousal-decay-step", type=float, default=0.2)
    ap.add_argument("--valence-recovery-step", type=float, default=0.15)
    ap.add_argument("--cooldown-event-out", type=Path, default=DEFAULT_COOLDOWN_EVENT_OUT)
    ap.add_argument(
        "--cooldown-event-jsonl",
        type=Path,
        nargs="?",
        const=DEFAULT_COOLDOWN_EVENT_JSONL,
        default=None,
    )
    ap.add_argument("--no-write-state", action="store_true")
    args = ap.parse_args()

    prev_path = args.prev_state_json or args.state_json
    prev_state = _read_json(prev_path)

    if args.chain_json and args.chain_json.is_file():
        chain = _read_json(args.chain_json)
        tv, ta = _target_va_from_chain(chain)
    elif args.target_valence is not None and args.target_arousal is not None:
        tv, ta = float(args.target_valence), float(args.target_arousal)
    else:
        ap.error("Provide --chain-json or both --target-valence and --target-arousal.")

    row, next_state = build_trajectory_row(
        session_id=args.session_id,
        turn_index=args.turn_index,
        target_valence=tv,
        target_arousal=ta,
        prev_state=prev_state,
        ema_alpha=float(args.ema_alpha),
        sasang_base=args.sasang_base,
        status=args.status,
        note=args.note,
    )
    thresholds_obj = {
        "high_arousal_cut": float(args.high_arousal_cut),
        "low_valence_cut": float(args.low_valence_cut),
        "arousal_decay_step": float(args.arousal_decay_step),
        "valence_recovery_step": float(args.valence_recovery_step),
    }
    cooldown_event: dict[str, Any]
    if args.enable_cooldown:
        current = dict(row.get("trajectory", {}).get("current_va") or {})
        cooldown = _apply_cooldown(
            valence=float(current.get("valence", 0.0)),
            arousal=float(current.get("arousal", 0.0)),
            high_arousal_cut=float(args.high_arousal_cut),
            low_valence_cut=float(args.low_valence_cut),
            arousal_decay_step=float(args.arousal_decay_step),
            valence_recovery_step=float(args.valence_recovery_step),
        )
        row["cooldown_control"] = {
            "policy_id": args.cooldown_policy_id,
            "enabled": True,
            **cooldown,
            "thresholds": dict(thresholds_obj),
        }
        row["trajectory"]["current_va"] = dict(cooldown["after_va"])
        next_state["current_va"] = dict(cooldown["after_va"])
        next_state["cooldown_last_applied"] = bool(cooldown["applied"])
        status_in = str(row.get("status") or "TRACKING_ACTIVE")
        status_out = "COOLDOWN_ACTIVE" if bool(cooldown["applied"]) else status_in
        row["status"] = status_out
        cooldown_event = {
            "schema": "va_cooldown_event_v1",
            "policy_id": args.cooldown_policy_id,
            "session_id": row["session_id"],
            "turn_index": row["turn_index"],
            "timestamp_utc": row["timestamp_utc"],
            "applied": bool(cooldown["applied"]),
            "reasons": list(cooldown["reasons"]),
            "thresholds": dict(thresholds_obj),
            "before_va": dict(cooldown["before_va"]),
            "after_va": dict(cooldown["after_va"]),
            "status_in": status_in,
            "status_out": status_out,
            "track_wall": ["NON_GATING", "ADVISORY_ONLY", "B_TRACK_RESEARCH"],
        }
    else:
        cur = dict(row.get("trajectory", {}).get("current_va") or {})
        cv, ca = _clip_va(float(cur.get("valence", 0.0)), float(cur.get("arousal", 0.0)))
        status_line = str(row.get("status") or "TRACKING_ACTIVE")
        cooldown_event = {
            "schema": "va_cooldown_event_v1",
            "policy_id": str(args.cooldown_policy_id),
            "session_id": row["session_id"],
            "turn_index": row["turn_index"],
            "timestamp_utc": row["timestamp_utc"],
            "applied": False,
            "reasons": [],
            "thresholds": dict(thresholds_obj),
            "before_va": {"valence": cv, "arousal": ca},
            "after_va": {"valence": cv, "arousal": ca},
            "status_in": status_line,
            "status_out": status_line,
            "track_wall": ["NON_GATING", "ADVISORY_ONLY", "B_TRACK_RESEARCH"],
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.no_write_state:
        args.state_json.parent.mkdir(parents=True, exist_ok=True)
        args.state_json.write_text(json.dumps(next_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.jsonl_log is not None:
        _append_jsonl(args.jsonl_log, row)
    args.cooldown_event_out.parent.mkdir(parents=True, exist_ok=True)
    args.cooldown_event_out.write_text(json.dumps(cooldown_event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.cooldown_event_jsonl is not None:
        _append_jsonl(args.cooldown_event_jsonl, cooldown_event)

    print(json.dumps({"ok": True, "out": str(args.out), "current_va": row["trajectory"]["current_va"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
