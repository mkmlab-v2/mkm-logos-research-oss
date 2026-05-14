#!/usr/bin/env python3
"""Run Pack 0-B deterministic LoRA pipeline with strict track-wall separation.

Flow:
1) Convert golden JSONL -> SFT instruction/output JSONL
2) Dataset contract eval (schema + forbidden-token hygiene)
3) Optional short LoRA training (fallback trainer)
4) Optional alignment eval (`run_myeongri_deterministic_lora_inference_eval_v1.py`) on a
   holdout golden file (default: split `locked_eval` only)

This script keeps symbolic/advisory layers out of supervision by enforcing
the existing Pack 0-B schema/eval gates before any training step.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, cwd: Path) -> int:
    print("[pack0b-pipeline] " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd))
    return int(proc.returncode)


def resolve_inference_profile_key(
    train_profile: str, inference_profile_key: str | None
) -> str:
    """Pick inference eval profile-key so base model matches the trained adapter.

    When ``--inference-profile-key`` is omitted, reuse ``--profile`` if set;
    otherwise fall back to ``train_default`` (CLI-only train without profile JSON).
    """
    if inference_profile_key is not None:
        return inference_profile_key
    p = (train_profile or "").strip()
    return p if p else "train_default"


def _resolve_profile(profile_json: Path, profile_key: str) -> dict[str, str]:
    obj = json.loads(profile_json.read_text(encoding="utf-8"))
    prof = ((obj.get("profiles") or {}).get(profile_key) or {})
    if not isinstance(prof, dict):
        raise SystemExit(f"invalid profile entry: {profile_key}")
    model_id = str(prof.get("model_id") or "").strip()
    if not model_id:
        raise SystemExit(f"profile '{profile_key}' missing model_id: {profile_json}")
    return {
        "model_name": model_id,
        "max_seq_length": str(int(prof.get("max_seq_length", 4096))),
        "batch_size": str(int(prof.get("batch_size", 1))),
        "grad_accum": str(int(prof.get("grad_accum", 2))),
        "learning_rate": str(float(prof.get("learning_rate", 0.00015))),
        "lora_r": str(int(prof.get("lora_r", 16))),
        "lora_alpha": str(int(prof.get("lora_alpha", 32))),
        "lora_dropout": str(float(prof.get("lora_dropout", 0.05))),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Pack 0-B deterministic LoRA pipeline runner")
    ap.add_argument(
        "--golden-jsonl",
        type=Path,
        default=ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl",
    )
    ap.add_argument(
        "--sft-jsonl",
        type=Path,
        default=ROOT / "data/training/myeongri_deterministic_lora_sft_train_v1.jsonl",
    )
    ap.add_argument(
        "--fit-report-out",
        type=Path,
        default=ROOT / "reports/myeongri_deterministic_lora_golden_fit_latest.json",
    )
    ap.add_argument("--run-train", action="store_true", help="Execute fallback trainer after conversion/eval")
    ap.add_argument("--train-steps", type=int, default=5)
    ap.add_argument("--model-name", default="TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    ap.add_argument(
        "--profile-json",
        type=Path,
        default=ROOT / "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json",
    )
    ap.add_argument("--profile", default="", help="Optional profile key in --profile-json (e.g. golden_fit_smoke)")
    ap.add_argument("--max-seq-length", type=int, default=4096)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--learning-rate", type=float, default=0.00015)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--lora-dropout", type=float, default=0.05)
    ap.add_argument(
        "--adapter-out",
        type=Path,
        default=ROOT / "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_pipeline_latest",
    )
    ap.add_argument("--dry-run-train", action="store_true")
    ap.add_argument(
        "--print-train-config",
        action="store_true",
        help="Print resolved train config JSON and exit after convert+eval",
    )
    ap.add_argument(
        "--run-inference-eval",
        action="store_true",
        help="After training (or if --adapter-out exists), run Pack 0-B inference+alignment eval",
    )
    ap.add_argument(
        "--inference-eval-golden-jsonl",
        type=Path,
        default=None,
        help="Golden JSONL for alignment eval (default: same as --golden-jsonl)",
    )
    ap.add_argument(
        "--inference-eval-all-splits",
        action="store_true",
        help="Evaluate all rows in inference golden (omit --split locked_eval)",
    )
    ap.add_argument(
        "--inference-profile-key",
        default=None,
        help=(
            "Profile key for inference eval base model. "
            "Omitted: same as --profile when set, else train_default"
        ),
    )
    ap.add_argument(
        "--inference-predictions-jsonl",
        type=Path,
        default=ROOT / "reports/myeongri_deterministic_lora_locked_eval_predictions_latest.jsonl",
    )
    ap.add_argument(
        "--inference-report-json",
        type=Path,
        default=ROOT / "reports/myeongri_deterministic_lora_locked_eval_inference_eval_latest.json",
    )
    args = ap.parse_args()
    args.inference_profile_key = resolve_inference_profile_key(
        args.profile, args.inference_profile_key
    )

    if not args.golden_jsonl.is_file():
        raise SystemExit(f"missing golden jsonl: {args.golden_jsonl}")

    convert = [
        sys.executable,
        str(ROOT / "scripts/convert_myeongri_golden_to_sft_instruction_jsonl_v1.py"),
        "--input-jsonl",
        str(args.golden_jsonl),
        "--output-jsonl",
        str(args.sft_jsonl),
    ]
    if _run(convert, cwd=ROOT) != 0:
        return 1

    fit_eval = [
        sys.executable,
        str(ROOT / "scripts/eval_myeongri_deterministic_lora_golden_fit_v1.py"),
        "--input-jsonl",
        str(args.golden_jsonl),
        "--out",
        str(args.fit_report_out),
    ]
    if _run(fit_eval, cwd=ROOT) != 0:
        return 2

    if args.print_train_config:
        train_cfg = {
            "model_name": str(args.model_name),
            "max_seq_length": str(args.max_seq_length),
            "batch_size": str(args.batch_size),
            "grad_accum": str(args.grad_accum),
            "learning_rate": str(args.learning_rate),
            "lora_r": str(args.lora_r),
            "lora_alpha": str(args.lora_alpha),
            "lora_dropout": str(args.lora_dropout),
        }
        if args.profile:
            train_cfg = _resolve_profile(args.profile_json, args.profile)
        print(json.dumps({"profile": args.profile or None, "train_config": train_cfg}, ensure_ascii=False))
        return 0

    if not args.run_train:
        if args.run_inference_eval:
            if not args.adapter_out.is_dir():
                raise SystemExit(
                    f"--run-inference-eval requires adapter dir; missing: {args.adapter_out} "
                    "(run with --run-train first or point --adapter-out to an existing adapter)"
                )
            return _run_inference_eval_bundle(args)
        print("[pack0b-pipeline] completed convert+eval (training skipped)")
        return 0

    train_cfg = {
        "model_name": str(args.model_name),
        "max_seq_length": str(args.max_seq_length),
        "batch_size": str(args.batch_size),
        "grad_accum": str(args.grad_accum),
        "learning_rate": str(args.learning_rate),
        "lora_r": str(args.lora_r),
        "lora_alpha": str(args.lora_alpha),
        "lora_dropout": str(args.lora_dropout),
    }
    if args.profile:
        train_cfg = _resolve_profile(args.profile_json, args.profile)

    train = [
        sys.executable,
        str(ROOT / "scripts/train_mkm_prophecy_lora_windows_fallback_v1.py"),
        "--dataset-path",
        str(args.sft_jsonl),
        "--model-name",
        train_cfg["model_name"],
        "--max-seq-length",
        train_cfg["max_seq_length"],
        "--max-steps",
        str(args.train_steps),
        "--batch-size",
        train_cfg["batch_size"],
        "--grad-accum",
        train_cfg["grad_accum"],
        "--learning-rate",
        train_cfg["learning_rate"],
        "--lora-r",
        train_cfg["lora_r"],
        "--lora-alpha",
        train_cfg["lora_alpha"],
        "--lora-dropout",
        train_cfg["lora_dropout"],
        "--output-dir",
        str(args.adapter_out),
    ]
    if args.dry_run_train:
        train.append("--dry-run")
    rc = _run(train, cwd=ROOT)
    if rc != 0:
        return 3
    print("[pack0b-pipeline] completed convert+eval+train")
    if args.run_inference_eval:
        if args.dry_run_train:
            print("[pack0b-pipeline] skip inference-eval (--dry-run-train)")
            return 0
        if not args.adapter_out.is_dir():
            print(f"[pack0b-pipeline] skip inference-eval (adapter dir missing): {args.adapter_out}")
            return 4
        rc2 = _run_inference_eval_bundle(args)
        if rc2 != 0:
            return rc2
    return 0


def _run_inference_eval_bundle(args: argparse.Namespace) -> int:
    ie_golden = args.inference_eval_golden_jsonl or args.golden_jsonl
    if not ie_golden.is_file():
        raise SystemExit(f"missing inference-eval golden jsonl: {ie_golden}")
    adapter = args.adapter_out
    if not adapter.is_dir():
        raise SystemExit(f"missing adapter for inference eval: {adapter}")
    infer_cmd: list[str] = [
        sys.executable,
        str(ROOT / "scripts/run_myeongri_deterministic_lora_inference_eval_v1.py"),
        "--golden-jsonl",
        str(ie_golden),
        "--adapter-path",
        str(adapter),
        "--profile-key",
        str(args.inference_profile_key),
        "--predictions-jsonl",
        str(args.inference_predictions_jsonl),
        "--report-json",
        str(args.inference_report_json),
    ]
    if not args.inference_eval_all_splits:
        infer_cmd.extend(["--split", "locked_eval"])
    print("[pack0b-pipeline] inference-eval: " + " ".join(infer_cmd))
    return int(subprocess.run(infer_cmd, cwd=str(ROOT)).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
