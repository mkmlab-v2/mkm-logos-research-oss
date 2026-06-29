#!/usr/bin/env python3
"""Expanded locked_eval on existing Qwen 4-pack adapters (no retrain).

B-track / research_only — alignment metrics only; not production GO by itself.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ABLATION = ROOT / "reports/lora_tranche2_qwen4pack_train_ablation_latest.json"
DEFAULT_LOCKED = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
DEFAULT_OUT = ROOT / "reports/lora_tranche2_qwen4pack_locked_eval_expanded_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    print("[expanded_eval] " + " ".join(cmd))
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def build_report(
    *,
    ablation_json: Path,
    locked_eval: Path,
    eval_limit: int,
    profile_key: str,
    skip_if_report: bool = False,
    schema: str = "lora_tranche2_qwen4pack_locked_eval_expanded_v1",
    architecture_lane: str = "bench_4x40",
) -> dict[str, Any]:
    ablation = json.loads(ablation_json.read_text(encoding="utf-8-sig"))
    pack_results: list[dict[str, Any]] = []

    for pack in ablation.get("packs", []):
        adapter_dir = Path(str(pack.get("adapter_dir", "")))
        pack_dir = adapter_dir.parent
        report_path = pack_dir / "locked_eval_expanded_report.json"
        pred_path = pack_dir / "locked_eval_expanded_predictions.jsonl"

        eval_doc: dict[str, Any] = {"skipped": True, "reason": "adapter_missing"}
        if skip_if_report and report_path.is_file():
            rep = json.loads(report_path.read_text(encoding="utf-8"))
            eval_doc = {"exit_code": 0, "report": rep, "reused_existing_report": True}
        elif (adapter_dir / "adapter_model.safetensors").is_file():
            cmd = [
                sys.executable,
                str(ROOT / "scripts/run_myeongri_deterministic_lora_inference_eval_v1.py"),
                "--golden-jsonl",
                str(locked_eval),
                "--adapter-path",
                str(adapter_dir),
                "--profile-key",
                profile_key,
                "--predictions-jsonl",
                str(pred_path),
                "--report-json",
                str(report_path),
                "--split",
                "locked_eval",
            ]
            if eval_limit > 0:
                cmd.extend(["--limit", str(eval_limit)])
            rc = _run(cmd)
            rep: dict[str, Any] = {}
            if report_path.is_file():
                rep = json.loads(report_path.read_text(encoding="utf-8"))
            eval_doc = {"exit_code": rc, "report": rep}

        entry: dict[str, Any] = {
                "pack_id": pack.get("pack_id"),
                "bench_4x40_label": pack.get("bench_4x40_label"),
                "adapter_dir": str(adapter_dir),
                "eval_limit": eval_limit if eval_limit > 0 else "all",
                "locked_eval": eval_doc,
            }
        if pack.get("acode_state_id"):
            entry["acode_state_id"] = pack.get("acode_state_id")
        if pack.get("shard_mode"):
            entry["shard_mode"] = pack.get("shard_mode")
        pack_results.append(entry)

    rates = [
        float(p["locked_eval"]["report"].get("alignment_pass_rate") or 0)
        for p in pack_results
        if isinstance(p.get("locked_eval"), dict)
        and isinstance(p["locked_eval"].get("report"), dict)
        and p["locked_eval"]["report"].get("rows")
    ]
    mean_rate = sum(rates) / len(rates) if rates else None

    return {
        "schema": schema,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "architecture_lane": architecture_lane,
        "ablation_json": str(ablation_json),
        "eval_limit": eval_limit if eval_limit > 0 else None,
        "profile_key": profile_key,
        "packs": pack_results,
        "summary": {
            "pack_count": len(pack_results),
            "mean_alignment_pass_rate": round(mean_rate, 4) if mean_rate is not None else None,
            "per_pack_alignment_pass_rate": rates,
        },
        "verdict_ko": (
            f"Expanded locked_eval (limit={eval_limit if eval_limit > 0 else 'all'}): "
            f"mean alignment_pass_rate={mean_rate}. Smoke/ablation — not Track A KPI."
            if mean_rate is not None
            else "Expanded locked_eval: no rows scored."
        ),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Expanded locked_eval on Qwen multipack adapters (no retrain).")
    p.add_argument("--ablation-json", default=str(DEFAULT_ABLATION))
    p.add_argument("--locked-eval", default=str(DEFAULT_LOCKED))
    p.add_argument("--eval-limit", type=int, default=25, help="0 = all rows")
    p.add_argument("--profile-key", default="train_default")
    p.add_argument("--schema", default="lora_tranche2_qwen4pack_locked_eval_expanded_v1")
    p.add_argument(
        "--architecture-lane",
        default="bench_4x40",
        help="bench_4x40 or hier_12x75_hybrid (A-code 12-pack lane).",
    )
    p.add_argument(
        "--skip-if-report",
        action="store_true",
        help="Reuse pack locked_eval_expanded_report.json when present (resume).",
    )
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out

    report = build_report(
        ablation_json=Path(args.ablation_json),
        locked_eval=Path(args.locked_eval),
        eval_limit=int(args.eval_limit),
        profile_key=str(args.profile_key),
        skip_if_report=bool(args.skip_if_report),
        schema=str(args.schema),
        architecture_lane=str(args.architecture_lane),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "mean_alignment": report["summary"].get("mean_alignment_pass_rate")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
