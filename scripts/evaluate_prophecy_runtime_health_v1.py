#!/usr/bin/env python3
"""Evaluate runtime health for prophecy + live-trading boundary.

This script is a proactive guardrail for the "measurement runs, evolution stalled"
failure mode. It checks latest artifacts and emits a single health decision.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_HIT = ART / "prophecy_hit_rate_eval_latest.json"
DEFAULT_SCORE = ART / "btrack_prophecy_score_latest.json"
DEFAULT_HYPO = ART / "btrack_hypothesis_prophecy_latest.json"
# Ops closure SSOT: daily B-track shadow gates (see build_prophecy_promotion_gates_ssot_pointer_v1.py).
DEFAULT_GATES = ART / "prophecy_promotion_gates_daily_shadow_v1_latest.json"
DEFAULT_LIVE_AB = ART / "prophecy_live_ab_summary_v1_latest.json"
DEFAULT_OUT = ART / "prophecy_runtime_health_guard_latest.json"


@dataclass
class Finding:
    severity: str  # red|amber
    code: str
    message: str
    observed: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _max_neutral_streak(rows: list[dict[str, Any]]) -> int:
    streak = 0
    max_streak = 0
    sorted_rows = sorted(rows, key=lambda x: (str(x.get("eval_date") or ""), str(x.get("instrument") or "")))
    for row in sorted_rows:
        pred = str(row.get("predicted_direction") or "").strip().lower()
        if pred == "neutral":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def _analyze(
    hit_doc: dict[str, Any],
    score_doc: dict[str, Any],
    hypo_doc: dict[str, Any],
    gates_doc: dict[str, Any],
    live_doc: dict[str, Any],
    *,
    min_hit_rate: float,
    max_neutral_ratio: float,
    max_neutral_streak: int,
    allow_live_prophecy_separation: bool = False,
) -> tuple[list[Finding], dict[str, Any]]:
    findings: list[Finding] = []

    metrics = hit_doc.get("metrics") if isinstance(hit_doc.get("metrics"), dict) else {}
    hit_rate = float(metrics.get("price_directional_hit_rate") or 0.0)
    n_eval = int(metrics.get("n_evaluated") or 0)
    if n_eval > 0 and hit_rate < min_hit_rate:
        findings.append(
            Finding(
                severity="red",
                code="LOW_PRICE_HIT_RATE",
                message="Price directional hit-rate is below runtime threshold.",
                observed={"price_directional_hit_rate": hit_rate, "n_evaluated": n_eval, "threshold": min_hit_rate},
            )
        )

    llm_model = ""
    provenance = hypo_doc.get("provenance") if isinstance(hypo_doc.get("provenance"), dict) else {}
    if provenance:
        llm_model = str(provenance.get("llm_model") or "").strip()
    if "stub" in llm_model.lower():
        findings.append(
            Finding(
                severity="red",
                code="STUB_PREDICTOR_DETECTED",
                message="Hypothesis generator is still using stub heuristic model.",
                observed={"llm_model": llm_model},
            )
        )

    rows_raw = score_doc.get("rows") if isinstance(score_doc.get("rows"), list) else []
    rows = [r for r in rows_raw if isinstance(r, dict)]
    neutral_count = sum(1 for r in rows if str(r.get("predicted_direction") or "").strip().lower() == "neutral")
    neutral_ratio = (neutral_count / len(rows)) if rows else 0.0
    neutral_streak = _max_neutral_streak(rows)
    if rows and neutral_ratio > max_neutral_ratio:
        findings.append(
            Finding(
                severity="red",
                code="NEUTRAL_BIAS_TOO_HIGH",
                message="Predicted direction is excessively concentrated on neutral.",
                observed={"neutral_ratio": round(neutral_ratio, 6), "threshold": max_neutral_ratio, "rows": len(rows)},
            )
        )
    if neutral_streak > max_neutral_streak:
        findings.append(
            Finding(
                severity="amber",
                code="NEUTRAL_STREAK_LONG",
                message="Neutral prediction streak exceeded warning threshold.",
                observed={"max_neutral_streak": neutral_streak, "threshold": max_neutral_streak},
            )
        )

    score_inputs = score_doc.get("inputs") if isinstance(score_doc.get("inputs"), dict) else {}
    btc_csv = score_inputs.get("btc_csv")
    if btc_csv in (None, "", "null", "None"):
        findings.append(
            Finding(
                severity="red",
                code="BTC_LEG_MISSING",
                message="BTC input CSV is missing from score artifact.",
                observed={"btc_csv": btc_csv},
            )
        )

    auto_promote_ready = bool(gates_doc.get("auto_promote_ready"))
    all_gates_passed = bool(gates_doc.get("all_gates_passed"))
    live_status = str(live_doc.get("status") or "").strip().upper()
    live_env = live_doc.get("environment") if isinstance(live_doc.get("environment"), dict) else {}
    live_enable_trading = bool(live_env.get("status_enable_trading"))
    if live_enable_trading and (not auto_promote_ready or not all_gates_passed):
        if allow_live_prophecy_separation:
            findings.append(
                Finding(
                    severity="amber",
                    code="MODE_B_LIVE_PROPHECY_SEPARATION",
                    message="Live execution ON and prophecy gates not passed — expected under Operation Mode B (shadow prophecy).",
                    observed={
                        "live_status": live_status,
                        "status_enable_trading": live_enable_trading,
                        "auto_promote_ready": auto_promote_ready,
                        "all_gates_passed": all_gates_passed,
                    },
                )
            )
        else:
            findings.append(
                Finding(
                    severity="red",
                    code="GATE_LIVE_CONFLICT",
                    message="Live trading is enabled while latest promotion gates are not ready.",
                    observed={
                        "live_status": live_status,
                        "status_enable_trading": live_enable_trading,
                        "auto_promote_ready": auto_promote_ready,
                        "all_gates_passed": all_gates_passed,
                    },
                )
            )

    summary = {
        "price_directional_hit_rate": hit_rate,
        "n_evaluated": n_eval,
        "llm_model": llm_model or None,
        "neutral_ratio": round(neutral_ratio, 6),
        "max_neutral_streak": neutral_streak,
        "row_count": len(rows),
        "btc_csv_input": btc_csv,
        "auto_promote_ready": auto_promote_ready,
        "all_gates_passed": all_gates_passed,
        "live_status": live_status or None,
        "status_enable_trading": live_enable_trading,
    }
    return findings, summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Runtime guard for prophecy/live alignment.")
    ap.add_argument("--hit-rate-json", type=Path, default=DEFAULT_HIT)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPO)
    ap.add_argument("--gates-json", type=Path, default=DEFAULT_GATES)
    ap.add_argument("--live-ab-json", type=Path, default=DEFAULT_LIVE_AB)
    ap.add_argument("--min-hit-rate", type=float, default=0.45)
    ap.add_argument("--max-neutral-ratio", type=float, default=0.70)
    ap.add_argument("--max-neutral-streak", type=int, default=8)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--fail-on-red", action="store_true")
    ap.add_argument(
        "--operation-mode-b-shadow",
        action="store_true",
        help="Operation Mode B: live aroon ON + prophecy shadow gates not passed is expected (amber, not red).",
    )
    args = ap.parse_args()

    hit_doc = _load_json(args.hit_rate_json)
    score_doc = _load_json(args.score_json)
    hypo_doc = _load_json(args.hypothesis_json)
    gates_doc = _load_json(args.gates_json)
    live_doc = _load_json(args.live_ab_json)

    findings, summary = _analyze(
        hit_doc,
        score_doc,
        hypo_doc,
        gates_doc,
        live_doc,
        min_hit_rate=args.min_hit_rate,
        max_neutral_ratio=args.max_neutral_ratio,
        max_neutral_streak=args.max_neutral_streak,
        allow_live_prophecy_separation=args.operation_mode_b_shadow,
    )

    red_count = sum(1 for f in findings if f.severity == "red")
    amber_count = sum(1 for f in findings if f.severity == "amber")
    if red_count > 0:
        status = "red"
    elif amber_count > 0:
        status = "amber"
    else:
        status = "green"

    out = {
        "schema": "prophecy_runtime_health_guard_v1",
        "generated_at_utc": _utc_now(),
        "status": status,
        "should_pause_trading": bool(red_count > 0),
        "summary": summary,
        "finding_counts": {"red": red_count, "amber": amber_count},
        "findings": [
            {"severity": f.severity, "code": f.code, "message": f.message, "observed": f.observed}
            for f in findings
        ],
        "inputs": {
            "hit_rate_json": str(args.hit_rate_json),
            "score_json": str(args.score_json),
            "hypothesis_json": str(args.hypothesis_json),
            "gates_json": str(args.gates_json),
            "live_ab_json": str(args.live_ab_json),
            "thresholds": {
                "min_hit_rate": args.min_hit_rate,
                "max_neutral_ratio": args.max_neutral_ratio,
                "max_neutral_streak": args.max_neutral_streak,
            },
        },
    }

    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")

    if args.fail_on_red and red_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
