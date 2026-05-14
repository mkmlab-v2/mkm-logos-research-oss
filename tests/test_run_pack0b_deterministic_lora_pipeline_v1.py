from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def _load_pack0b_module(repo: Path):
    script = repo / "scripts" / "run_pack0b_deterministic_lora_pipeline_v1.py"
    spec = importlib.util.spec_from_file_location("pack0b_pipeline_v1", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_resolve_inference_profile_key_defaults() -> None:
    repo = Path(__file__).resolve().parents[1]
    mod = _load_pack0b_module(repo)
    assert mod.resolve_inference_profile_key("", None) == "train_default"
    assert mod.resolve_inference_profile_key("  ", None) == "train_default"
    assert mod.resolve_inference_profile_key("golden_fit_smoke", None) == "golden_fit_smoke"
    assert mod.resolve_inference_profile_key("golden_fit_smoke", "train_default") == "train_default"


def test_pack0b_pipeline_convert_eval_smoke(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "run_pack0b_deterministic_lora_pipeline_v1.py"
    golden = repo / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"
    sft_out = tmp_path / "sft.jsonl"
    fit_out = tmp_path / "fit.json"

    r = subprocess.run(
        [
            sys.executable,
            str(script),
            "--golden-jsonl",
            str(golden),
            "--sft-jsonl",
            str(sft_out),
            "--fit-report-out",
            str(fit_out),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert sft_out.is_file()
    assert fit_out.is_file()


def test_pack0b_pipeline_profile_resolution_smoke(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "run_pack0b_deterministic_lora_pipeline_v1.py"
    golden = repo / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"
    sft_out = tmp_path / "sft.jsonl"
    fit_out = tmp_path / "fit.json"

    r = subprocess.run(
        [
            sys.executable,
            str(script),
            "--golden-jsonl",
            str(golden),
            "--sft-jsonl",
            str(sft_out),
            "--fit-report-out",
            str(fit_out),
            "--run-train",
            "--dry-run-train",
            "--profile",
            "golden_fit_smoke",
            "--print-train-config",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    cfg_line = [ln for ln in r.stdout.splitlines() if ln.strip().startswith("{")][-1]
    payload = json.loads(cfg_line)
    assert payload["profile"] == "golden_fit_smoke"
    assert payload["train_config"]["model_name"] == "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


def test_pack0b_run_inference_eval_requires_adapter_dir(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "run_pack0b_deterministic_lora_pipeline_v1.py"
    golden = repo / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"
    sft_out = tmp_path / "sft.jsonl"
    fit_out = tmp_path / "fit.json"
    missing_adapter = tmp_path / "no_adapter_here"

    r = subprocess.run(
        [
            sys.executable,
            str(script),
            "--golden-jsonl",
            str(golden),
            "--sft-jsonl",
            str(sft_out),
            "--fit-report-out",
            str(fit_out),
            "--run-inference-eval",
            "--adapter-out",
            str(missing_adapter),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode != 0


def test_pack0b_dry_run_train_skips_inference_eval(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "run_pack0b_deterministic_lora_pipeline_v1.py"
    golden = repo / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"
    sft_out = tmp_path / "sft.jsonl"
    fit_out = tmp_path / "fit.json"
    adapter_dir = tmp_path / "adapter_placeholder"

    r = subprocess.run(
        [
            sys.executable,
            str(script),
            "--golden-jsonl",
            str(golden),
            "--sft-jsonl",
            str(sft_out),
            "--fit-report-out",
            str(fit_out),
            "--run-train",
            "--dry-run-train",
            "--run-inference-eval",
            "--adapter-out",
            str(adapter_dir),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "skip inference-eval" in r.stdout.lower() or "skip inference-eval" in (r.stderr or "").lower()
