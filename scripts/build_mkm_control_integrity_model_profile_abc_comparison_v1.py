#!/usr/bin/env python3
"""Build ABC profile comparison report from per-profile eval reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "model_profile_abc_comparison_latest.json"
DEFAULT_PROFILES_JSON = (
    WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "mkm_control_integrity_lora_model_profiles_v1.json"
)

PROFILE_KEY_BY_COMPARE_KEY = {
    "a_qwen25_base": "qwen_safe",
    "b_gemma3_upgrade": "gemma3_safe",
    "c_qwen3_research": "qwen3_safe",
}

DEFAULT_INPUTS = {
    "a_qwen25_base": WORKSPACE_ROOT / "reports" / "mkm_control_integrity_lora_eval_test_a_qwen25_base_latest.json",
    "b_gemma3_upgrade": WORKSPACE_ROOT / "reports" / "mkm_control_integrity_lora_eval_test_b_gemma3_upgrade_latest.json",
    "c_qwen3_research": WORKSPACE_ROOT / "reports" / "mkm_control_integrity_lora_eval_test_c_qwen3_research_latest.json",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"expected object json: {path}")
    return obj


def _load_profiles_ssot(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict):
        return None
    profiles = doc.get("profiles")
    if not isinstance(profiles, dict):
        return None
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build ABC comparison JSON from profile eval reports")
    ap.add_argument("--a", default=str(DEFAULT_INPUTS["a_qwen25_base"]))
    ap.add_argument("--b", default=str(DEFAULT_INPUTS["b_gemma3_upgrade"]))
    ap.add_argument("--c", default=str(DEFAULT_INPUTS["c_qwen3_research"]))
    ap.add_argument("--profiles-json", default=str(DEFAULT_PROFILES_JSON), help="LoRA profile SSOT JSON")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    # Golden test split: oracle (=expected_response) tops out near ~0.71 row_pass on SSOT v1.
    ap.add_argument(
        "--min-row-pass-rate",
        type=float,
        default=0.70,
        help="Gate threshold; default aligns with oracle ceiling on CI golden test split",
    )
    ap.add_argument(
        "--min-must-include-rate",
        type=float,
        default=0.70,
        help="Gate threshold; default aligns with oracle ceiling on CI golden test split",
    )
    args = ap.parse_args()

    inputs = {
        "a_qwen25_base": Path(args.a),
        "b_gemma3_upgrade": Path(args.b),
        "c_qwen3_research": Path(args.c),
    }
    out = Path(args.out)
    profiles_json_path = Path(args.profiles_json)
    if not profiles_json_path.is_absolute():
        profiles_json_path = WORKSPACE_ROOT / profiles_json_path
    ssot_doc = _load_profiles_ssot(profiles_json_path)

    profiles: dict[str, Any] = {}
    errors: list[str] = []

    for key, path in inputs.items():
        if not path.is_absolute():
            path = WORKSPACE_ROOT / path
        if not path.is_file():
            errors.append(f"missing report: {key} -> {path}")
            continue
        rep = _load_json(path)
        s = rep.get("summary", {})
        row_pass = float(s.get("row_pass_rate", 0.0))
        must_include = float(s.get("must_include_pass_rate", 0.0))
        coverage = float(s.get("coverage_rate", 0.0))
        gate_pass = (
            row_pass >= args.min_row_pass_rate
            and must_include >= args.min_must_include_rate
            and coverage >= 0.99
            and rep.get("ok", False) is True
        )
        training_hyperparams: dict[str, Any] | None = None
        if ssot_doc:
            pk = PROFILE_KEY_BY_COMPARE_KEY.get(key)
            raw_profiles = ssot_doc.get("profiles")
            if pk and isinstance(raw_profiles, dict) and pk in raw_profiles:
                hp = raw_profiles[pk]
                if isinstance(hp, dict):
                    training_hyperparams = {
                        "profile_ssot_key": pk,
                        "model_id": hp.get("model_id"),
                        "unsloth_model_id": hp.get("unsloth_model_id"),
                        "max_seq_length": hp.get("max_seq_length"),
                        "batch_size": hp.get("batch_size"),
                        "grad_accum": hp.get("grad_accum"),
                        "lora_r": hp.get("lora_r"),
                        "lora_alpha": hp.get("lora_alpha"),
                        "lora_dropout": hp.get("lora_dropout"),
                        "learning_rate": hp.get("learning_rate"),
                        "role": hp.get("role"),
                    }

        entry: dict[str, Any] = {
            "report_path": str(path),
            "row_pass_rate": row_pass,
            "must_include_pass_rate": must_include,
            "must_not_include_pass_rate": float(s.get("must_not_include_pass_rate", 0.0)),
            "coverage_rate": coverage,
            "gate_pass": gate_pass,
        }
        if training_hyperparams:
            entry["training_hyperparams"] = training_hyperparams
        profiles[key] = entry

    leader = None
    if profiles:
        leader = max(profiles.items(), key=lambda kv: kv[1]["row_pass_rate"])[0]

    result = {
        "schema": "mkm_control_integrity_model_profile_abc_comparison_v1",
        "profiles_ssot_path": str(profiles_json_path) if ssot_doc else None,
        "quantization_ssot": ssot_doc.get("quantization") if ssot_doc else None,
        "profiles": profiles,
        "leader_by_row_pass_rate": leader,
        "gate_policy": {
            "min_row_pass_rate": args.min_row_pass_rate,
            "min_must_include_pass_rate": args.min_must_include_rate,
            "min_coverage_rate": 0.99,
        },
        "errors": errors,
        "ok": len(errors) == 0,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"profiles={len(profiles)}")
    print(f"errors={len(errors)}")
    print(f"leader={leader}")
    print(f"out={out}")
    return 0 if len(errors) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
