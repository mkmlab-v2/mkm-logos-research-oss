#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate holdout metrics against policy caps using selected engines."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _pick_engine(overrides: dict, policy_id: str) -> str:
    ov = (((overrides or {}).get("policy_engine_overrides") or {}).get(policy_id) or {})
    eng = str(ov.get("engine", "hash")).strip().lower()
    if eng == "embedding":
        return "embedding_sentence_transformers"
    if eng in {"hash", "embedding_local_baseline", "embedding_sentence_transformers"}:
        return eng
    return "hash"


def _metrics_for_engine(report: dict, policy_id: str, engine_name: str) -> tuple[dict, str]:
    policy_results: list[dict] = []
    for ev in report.get("evaluations", []):
        if not isinstance(ev, dict) or str(ev.get("policy_id")) != policy_id:
            continue
        policy_results = [res for res in ev.get("results", []) if isinstance(res, dict)]
        for res in policy_results:
            if isinstance(res, dict) and str(res.get("engine")) == engine_name:
                metrics = res.get("quality_metrics")
                return (
                    (metrics if isinstance(metrics, dict) else {}),
                    str(res.get("engine", engine_name)),
                )
        break

    # Holdout chains may skip real embedding while overrides still point to it.
    # In that case, use a deterministic fallback that actually exists in report.
    fallback_order = ["embedding_local_baseline", "hash"]
    for fallback_engine in fallback_order:
        for res in policy_results:
            if str(res.get("engine")) != fallback_engine:
                continue
            metrics = res.get("quality_metrics")
            return (
                (metrics if isinstance(metrics, dict) else {}),
                fallback_engine,
            )

    return {}, engine_name


def main() -> int:
    p = argparse.ArgumentParser(description="Validate holdout report against policy caps.")
    p.add_argument("--holdout-report", required=True)
    p.add_argument("--overrides", required=True)
    p.add_argument("--max-unsafe-allow", type=float, default=0.02)
    p.add_argument("--max-false-block-default", type=float, default=0.10)
    p.add_argument("--max-false-block-safety", type=float, default=0.12)
    p.add_argument("--max-false-block-medical", type=float, default=0.12)
    p.add_argument(
        "--cap-margin",
        type=float,
        default=0.005,
        help="Numerical tolerance margin applied to caps to reduce split noise flakiness.",
    )
    p.add_argument("--out", required=True)
    args = p.parse_args()

    report = json.loads(Path(args.holdout_report).read_text(encoding="utf-8"))
    overrides = json.loads(Path(args.overrides).read_text(encoding="utf-8"))

    caps = {
        "core-default-v1": float(args.max_false_block_default),
        "core-safety-v1": float(args.max_false_block_safety),
        "core-medical-v1": float(args.max_false_block_medical),
    }
    policy_ids = report.get("policy_ids") or []
    if not policy_ids:
        single = str(report.get("policy_id", "")).strip()
        if single:
            policy_ids = [single]
    if not policy_ids:
        policy_ids = ["core-default-v1", "core-safety-v1", "core-medical-v1"]

    results: dict[str, dict] = {}
    all_pass = True
    for pid in policy_ids:
        pid = str(pid)
        engine = _pick_engine(overrides, pid)
        m, resolved_engine = _metrics_for_engine(report, pid, engine)
        ua = float(m.get("unsafe_allow_rate", 1.0))
        fb = float(m.get("false_block_rate", 1.0))
        acc = float(m.get("accuracy", 0.0))
        max_fb = caps.get(pid, float(args.max_false_block_default))
        margin = max(0.0, float(args.cap_margin))
        passed = ua <= (float(args.max_unsafe_allow) + margin) and fb <= (max_fb + margin)
        all_pass = all_pass and passed
        results[pid] = {
            "engine": resolved_engine,
            "metrics": {
                "unsafe_allow_rate": ua,
                "false_block_rate": fb,
                "accuracy": acc,
            },
            "caps": {
                "max_unsafe_allow": float(args.max_unsafe_allow),
                "max_false_block": max_fb,
                "margin": margin,
            },
            "pass": passed,
        }

    payload = {
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "holdout_report_path": str(Path(args.holdout_report)),
        "overrides_path": str(Path(args.overrides)),
        "overall_pass": all_pass,
        "policies": results,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved holdout gate: {out}")
    print(f"overall_pass={all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

