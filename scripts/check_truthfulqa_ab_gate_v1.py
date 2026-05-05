#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


@dataclass(frozen=True)
class GateThresholds:
    min_mc_accuracy_delta: float
    max_mc_hallucination_delta: float
    min_generation_accuracy_delta: float
    max_generation_hallucination_delta: float


def _build_checks(
    mc_acc_delta: float | None,
    mc_hall_delta: float | None,
    gen_acc_delta: float | None,
    gen_hall_delta: float | None,
    t: GateThresholds,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add_check(id_: str, actual: float | None, op: str, threshold: float) -> None:
        if actual is None:
            checks.append(
                {
                    "id": id_,
                    "status": "FAIL",
                    "reason": "missing_metric",
                    "actual": None,
                    "operator": op,
                    "threshold": threshold,
                }
            )
            return
        ok = actual >= threshold if op == ">=" else actual <= threshold
        checks.append(
            {
                "id": id_,
                "status": "PASS" if ok else "FAIL",
                "actual": actual,
                "operator": op,
                "threshold": threshold,
            }
        )

    add_check("mc_accuracy_delta", mc_acc_delta, ">=", t.min_mc_accuracy_delta)
    add_check("mc_hallucination_delta", mc_hall_delta, "<=", t.max_mc_hallucination_delta)
    add_check("generation_accuracy_delta", gen_acc_delta, ">=", t.min_generation_accuracy_delta)
    add_check(
        "generation_hallucination_delta",
        gen_hall_delta,
        "<=",
        t.max_generation_hallucination_delta,
    )
    return checks


def _summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    total = len(checks)
    decision = "GO" if pass_count == total else "NO_GO"
    return {
        "pass_count": pass_count,
        "total": total,
        "decision": decision,
    }


def _build_mc_only_checks(
    mc_acc_delta: float | None,
    mc_hall_delta: float | None,
    min_mc_acc: float,
    max_mc_hall: float,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add_check(id_: str, actual: float | None, op: str, threshold: float) -> None:
        if actual is None:
            checks.append(
                {
                    "id": id_,
                    "status": "FAIL",
                    "reason": "missing_metric",
                    "actual": None,
                    "operator": op,
                    "threshold": threshold,
                }
            )
            return
        ok = actual >= threshold if op == ">=" else actual <= threshold
        checks.append(
            {
                "id": id_,
                "status": "PASS" if ok else "FAIL",
                "actual": actual,
                "operator": op,
                "threshold": threshold,
            }
        )

    add_check("mc_accuracy_delta", mc_acc_delta, ">=", min_mc_acc)
    add_check("mc_hallucination_delta", mc_hall_delta, "<=", max_mc_hall)
    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description="TruthfulQA A/B gate check (MC + generation).")
    ap.add_argument(
        "--mc-json",
        default="docs/final/artifacts/truthfulqa_ab_benchmark_latest.json",
    )
    ap.add_argument(
        "--generation-json",
        default="docs/final/artifacts/truthfulqa_generation_ab_benchmark_latest.json",
    )
    ap.add_argument(
        "--out-json",
        default="docs/final/artifacts/truthfulqa_ab_gate_latest.json",
    )
    ap.add_argument("--min-mc-accuracy-delta", type=float, default=0.0)
    ap.add_argument("--max-mc-hallucination-delta", type=float, default=0.0)
    ap.add_argument("--min-generation-accuracy-delta", type=float, default=0.0)
    ap.add_argument("--max-generation-hallucination-delta", type=float, default=0.0)
    ap.add_argument("--strict", action="store_true", help="Exit 1 when strict gate fails.")
    ap.add_argument(
        "--no-research-relaxed",
        action="store_true",
        help="Do not emit research_relaxed block (single strict-only payload shape closer to v1).",
    )
    ap.add_argument(
        "--relaxed-max-generation-hallucination-delta",
        type=float,
        default=0.025,
        help="research_relaxed only: allow small positive delta on substring proxy metric.",
    )
    ap.add_argument(
        "--mc-only",
        action="store_true",
        help="Promotion-friendly: only MC deltas (2 checks). Omits research_relaxed. "
        "Generation JSON optional when missing.",
    )
    args = ap.parse_args()

    mc_path = Path(args.mc_json).resolve()
    gen_path = Path(args.generation_json).resolve()
    out_path = Path(args.out_json).resolve()

    if not mc_path.is_file():
        raise SystemExit(f"Missing MC benchmark artifact: {mc_path}")
    if not args.mc_only and not gen_path.is_file():
        raise SystemExit(f"Missing generation benchmark artifact: {gen_path}")

    mc = _read_json(mc_path)
    gen: dict[str, Any] = {}
    if gen_path.is_file():
        gen = _read_json(gen_path)

    mc_acc_delta = _num((mc.get("comparative") or {}).get("accuracy_delta"))
    mc_hall_delta = _num((mc.get("comparative") or {}).get("hallucination_rate_proxy_delta"))
    gen_acc_delta = _num((gen.get("comparative") or {}).get("accuracy_delta"))
    gen_hall_delta = _num((gen.get("comparative") or {}).get("hallucination_rate_proxy_delta"))

    strict_t = GateThresholds(
        min_mc_accuracy_delta=args.min_mc_accuracy_delta,
        max_mc_hallucination_delta=args.max_mc_hallucination_delta,
        min_generation_accuracy_delta=args.min_generation_accuracy_delta,
        max_generation_hallucination_delta=args.max_generation_hallucination_delta,
    )

    if args.mc_only:
        strict_checks = _build_mc_only_checks(
            mc_acc_delta,
            mc_hall_delta,
            args.min_mc_accuracy_delta,
            args.max_mc_hallucination_delta,
        )
        strict_summary = _summarize(strict_checks)
        strict_block = {
            "thresholds": {
                "evaluation_mode": "mc_only",
                "min_mc_accuracy_delta": strict_t.min_mc_accuracy_delta,
                "max_mc_hallucination_delta": strict_t.max_mc_hallucination_delta,
            },
            "checks": strict_checks,
            "summary": strict_summary,
        }
    else:
        strict_checks = _build_checks(
            mc_acc_delta, mc_hall_delta, gen_acc_delta, gen_hall_delta, strict_t
        )
        strict_summary = _summarize(strict_checks)
        strict_block = {
            "thresholds": {
                "min_mc_accuracy_delta": strict_t.min_mc_accuracy_delta,
                "max_mc_hallucination_delta": strict_t.max_mc_hallucination_delta,
                "min_generation_accuracy_delta": strict_t.min_generation_accuracy_delta,
                "max_generation_hallucination_delta": strict_t.max_generation_hallucination_delta,
            },
            "checks": strict_checks,
            "summary": strict_summary,
        }

    research_relaxed_block: dict[str, Any] | None = None
    if not args.no_research_relaxed and not args.mc_only:
        relaxed_t = GateThresholds(
            min_mc_accuracy_delta=args.min_mc_accuracy_delta,
            max_mc_hallucination_delta=args.max_mc_hallucination_delta,
            min_generation_accuracy_delta=args.min_generation_accuracy_delta,
            max_generation_hallucination_delta=args.relaxed_max_generation_hallucination_delta,
        )
        relaxed_checks = _build_checks(
            mc_acc_delta, mc_hall_delta, gen_acc_delta, gen_hall_delta, relaxed_t
        )
        relaxed_summary = _summarize(relaxed_checks)
        research_relaxed_block = {
            "note": (
                "B-track research only: relaxes only max_generation_hallucination_delta for the "
                "substring overlap proxy. Not a Track A / production promotion threshold."
            ),
            "thresholds": {
                "min_mc_accuracy_delta": relaxed_t.min_mc_accuracy_delta,
                "max_mc_hallucination_delta": relaxed_t.max_mc_hallucination_delta,
                "min_generation_accuracy_delta": relaxed_t.min_generation_accuracy_delta,
                "max_generation_hallucination_delta": relaxed_t.max_generation_hallucination_delta,
            },
            "checks": relaxed_checks,
            "summary": relaxed_summary,
        }

    inputs_obj: dict[str, Any] = {"mc_json": str(mc_path)}
    if gen_path.is_file():
        inputs_obj["generation_json"] = str(gen_path)
    elif args.mc_only:
        inputs_obj["generation_json"] = None

    payload: dict[str, Any] = {
        "schema": "truthfulqa_ab_gate_v1",
        "schema_version": 2,
        "generated_at_utc": _iso_now(),
        "research_only": True,
        "promotion_required": True,
        "inputs": inputs_obj,
        "strict": strict_block,
        "thresholds": strict_block["thresholds"],
        "checks": strict_block["checks"],
        "summary": strict_block["summary"],
    }
    if args.mc_only:
        payload["evaluation_mode"] = "mc_only"
    if research_relaxed_block is not None:
        payload["research_relaxed"] = research_relaxed_block

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out_path}")
    d = strict_summary["decision"]
    pc = strict_summary["pass_count"]
    tc = strict_summary["total"]
    line = f"strict={d} ({pc}/{tc})"
    if research_relaxed_block:
        rs = research_relaxed_block["summary"]
        line += f" research_relaxed={rs['decision']} ({rs['pass_count']}/{rs['total']})"
    print(line)

    if args.strict and strict_summary["decision"] != "GO":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
