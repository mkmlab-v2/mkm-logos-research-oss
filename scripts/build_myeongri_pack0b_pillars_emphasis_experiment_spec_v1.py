"""Write Pack 0-B pillars-only + birth-emphasis controlled experiment spec (GPU-free)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "reports/myeongri_pack0b_adapter_locked_triage_latest.json"
OUT = ROOT / "reports/myeongri_pack0b_pillars_emphasis_experiment_spec_v1_latest.json"

GOLDEN_TRAIN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl"
GOLDEN_LOCKED = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
SFT_OUT = ROOT / "data/training/myeongri_pillars_only_sft_birth_emphasis_v1.jsonl"
ADAPTER_OUT = ROOT / "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_pillars_emphasis_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    triage = {}
    if TRIAGE.is_file():
        triage = json.loads(TRIAGE.read_text(encoding="utf-8-sig"))

    spec = {
        "schema": "myeongri_pack0b_pillars_emphasis_experiment_spec_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "title": "Pack 0-B tier-0 pillars-only + birth-emphasis SFT (controlled)",
        "premise": {
            "dominant_failure_mode": triage.get("dominant_failure_mode", "model_mode_collapse_while_golden_ok"),
            "oracle_ceiling": triage.get("eval_ceiling_oracle"),
            "triage_artifact": str(TRIAGE.relative_to(ROOT)).replace("\\", "/"),
            "note_ko": (
                "골든·엔진 100% — 라벨 SSOT 유효. E2E LoRA는 parse는 되나 four_pillars 0% mode collapse. "
                "하이브리드(RF/XGB) 76%는 LoRA 상한이 아님."
            ),
        },
        "hypothesis": (
            "Tier-0 curriculum (4-key myeongri_pillars_only_v1 JSON) + instruction birth-emphasis "
            "reduces ganji mode collapse vs full compact / default completion SFT."
        ),
        "model": {
            "base": "Qwen/Qwen2.5-7B-Instruct",
            "profile_key": "train_default",
            "profiles_json": "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json",
        },
        "data": {
            "golden_train": str(GOLDEN_TRAIN.relative_to(ROOT)).replace("\\", "/"),
            "golden_locked_eval": str(GOLDEN_LOCKED.relative_to(ROOT)).replace("\\", "/"),
            "sft_jsonl": str(SFT_OUT.relative_to(ROOT)).replace("\\", "/"),
            "train_rows": 1000,
            "train_rows_note": "Full bulk train.jsonl converted; step budget 100 (not row subsample).",
            "curriculum": "pillars_only_v1",
            "birth_emphasis": True,
            "supervision_schema": "myeongri_pillars_only_v1",
        },
        "train": {
            "max_steps": 100,
            "probe_steps": [20, 40, 60, 80, 100],
            "early_stop_rule": "If locked25 pillars_alignment_pass_rate == 0 at step 50, STOP and run label crosscheck only (no step extension).",
            "adapter_out": str(ADAPTER_OUT.relative_to(ROOT)).replace("\\", "/"),
            "trainer": "scripts/train_mkm_prophecy_lora_windows_fallback_v1.py",
        },
        "eval": {
            "split": "locked_eval",
            "holdout_n": 25,
            "metrics_primary": "pillars_alignment_pass_rate",
            "metrics_secondary": ["parse_ok_rate", "four_pillars_by_key", "ilgan_match_rate"],
            "success_bar": {"pillars_alignment_pass_rate_gte": 0.10},
            "failure_bar": {"pillars_alignment_pass_rate_at_step_50_eq": 0.0},
            "eval_script": "scripts/run_myeongri_deterministic_lora_inference_eval_v1.py",
            "eval_flags": ["--pillars-only-curriculum"],
        },
        "commands": {
            "prep_sft": (
                f"py scripts/build_myeongri_pillars_only_sft_v1.py "
                f"--input-jsonl {GOLDEN_TRAIN.relative_to(ROOT)} "
                f"--output-jsonl {SFT_OUT.relative_to(ROOT)} --birth-emphasis"
            ),
            "train_100": (
                f"py scripts/train_mkm_prophecy_lora_windows_fallback_v1.py "
                f"--dataset-path {SFT_OUT.relative_to(ROOT)} "
                f"--model-name Qwen/Qwen2.5-7B-Instruct --profile-json "
                f"docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json "
                f"--max-steps 100 --output-dir {ADAPTER_OUT.relative_to(ROOT)}"
            ),
            "eval_locked25": (
                f"py scripts/run_myeongri_deterministic_lora_inference_eval_v1.py "
                f"--golden-jsonl {GOLDEN_LOCKED.relative_to(ROOT)} "
                f"--adapter-path {ADAPTER_OUT.relative_to(ROOT)} "
                f"--profile-key train_default --pillars-only-curriculum "
                f"--report-json reports/myeongri_pack0b_pillars_emphasis_locked25_eval.json"
            ),
            "refresh_triage": "py scripts/build_myeongri_pack0b_adapter_locked_triage_v1.py",
            "label_crosscheck_if_stuck": "py scripts/build_myeongri_pillars_engine_crosscheck_v1.py",
        },
        "explicit_non_goals": [
            "Track A / MS KPI promotion",
            "live trading or external send",
            "W1-W4 RC factory re-run without input change",
            "Nemotron 16GB QLoRA retry loop",
            "offline_4d Logos bulk merge",
            "Treat pipeline GO as semantic pillars GO",
        ],
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
        },
    }

    locked25_path = ROOT / "reports/myeongri_pack0b_pillars_emphasis_locked25_eval.json"
    locked100_path = ROOT / "reports/myeongri_pack0b_pillars_emphasis_locked_eval_latest.json"
    outcome: dict = {"status": "pending", "primary_follow_on": "harness_v2_engine_plus_interpret"}
    if locked100_path.is_file():
        ev100 = json.loads(locked100_path.read_text(encoding="utf-8-sig"))
        align = float(ev100.get("pillars_alignment_pass_rate", ev100.get("alignment_pass_rate", 0.0)))
        parse_ok = float(ev100.get("parse_ok_rate", 0.0))
        outcome = {
            "status": "FAILED" if align < 0.10 else "PASS_CANDIDATE",
            "verdict": "hypothesis_rejected" if align < 0.10 else "hypothesis_partial",
            "completed_at_utc": _utc_now(),
            "locked25_report": str(locked25_path.relative_to(ROOT)).replace("\\", "/"),
            "locked100_report": str(locked100_path.relative_to(ROOT)).replace("\\", "/"),
            "metrics": {
                "locked100_rows": int(ev100.get("rows", 0)),
                "parse_ok_rate": parse_ok,
                "pillars_alignment_pass_rate": align,
                "success_bar_gte": 0.10,
            },
            "primary_follow_on": "harness_v2_engine_plus_interpret",
            "note_ko": "LoRA E2E four_pillars 0% — 엔진 결정론 + interpret LoRA 라우팅으로 전환.",
        }
    spec["experiment_outcome"] = outcome

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
