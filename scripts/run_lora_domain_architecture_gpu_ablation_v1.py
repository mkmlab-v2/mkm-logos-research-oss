#!/usr/bin/env python3
"""GPU ablation: adapter swap + warm inference cost vs pack-count architectures.

B-track / research_only. Reuses Pack 0-B inference loader; does not promote Track A.
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SWEEP = ROOT / "reports/lora_domain_architecture_sweep_latest.json"
DEFAULT_EXTRAP = ROOT / "reports/lora_pack_latency_extrapolation_latest.json"
DEFAULT_GOLDEN = ROOT / "tests/fixtures/myeongri_deterministic_lora_golden_sample_v1.jsonl"
DEFAULT_PROFILE = ROOT / "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json"
DEFAULT_ADAPTER = (
    ROOT / "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_train_default_completion"
)
DEFAULT_OUT = ROOT / "reports/lora_domain_architecture_gpu_ablation_latest.json"

ARCHITECTURE_SCENARIOS = (
    {"id": "bench_4x40", "packs": 4},
    {"id": "hier_12x75_hybrid", "packs": 12},
    {"id": "flat_20x40", "packs": 20},
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _import_inference_helpers():
    path = ROOT / "scripts/run_myeongri_deterministic_lora_inference_eval_v1.py"
    spec = importlib.util.spec_from_file_location("myeongri_lora_infer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import inference helpers from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gpu_info() -> dict[str, Any]:
    info: dict[str, Any] = {"cuda_available": False}
    try:
        import torch

        info["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            info["device_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info["total_vram_gb"] = round(float(props.total_memory) / (1024**3), 2)
    except Exception as exc:  # pragma: no cover
        info["error"] = str(exc)
    return info


def _pick_instruction(golden_path: Path) -> str:
    mod = _import_inference_helpers()
    rows = mod._load_jsonl(golden_path)
    if not rows:
        raise SystemExit(f"no golden rows in {golden_path}")
    return mod._instruction_from_golden_row(rows[0])


def _measure_swap_session(
    *,
    model_name: str,
    adapter_path: Path,
    instruction: str,
    load_in_4bit: bool,
    bnb_4bit_quant_type: str,
    max_new_tokens: int,
    swap_probes: int,
) -> dict[str, Any]:
    mod = _import_inference_helpers()
    import torch
    from peft import PeftModel

    t_base0 = time.perf_counter()
    base_model, tokenizer = mod._load_model_and_tokenizer(
        model_name,
        "",
        load_in_4bit=load_in_4bit,
        bnb_4bit_quant_type=bnb_4bit_quant_type,
    )
    base_load_sec = time.perf_counter() - t_base0

    attach_samples: list[float] = []
    infer_samples: list[float] = []
    for _ in range(max(1, swap_probes)):
        t_attach0 = time.perf_counter()
        model = PeftModel.from_pretrained(base_model, str(adapter_path))
        model.eval()
        attach_samples.append(time.perf_counter() - t_attach0)

        t_inf0 = time.perf_counter()
        _ = mod._generate_one(
            model,
            tokenizer,
            instruction,
            max_new_tokens=max_new_tokens,
            temperature=0.0,
            top_p=1.0,
            repetition_penalty=1.15,
            chat_leak_stop=True,
        )
        infer_samples.append(time.perf_counter() - t_inf0)

        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    del base_model
    del tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return {
        "base_load_sec": round(base_load_sec, 4),
        "adapter_attach_sec": round(statistics.mean(attach_samples), 4),
        "warm_inference_sec": round(statistics.mean(infer_samples), 4),
        "attach_samples_sec": [round(x, 4) for x in attach_samples],
        "infer_samples_sec": [round(x, 4) for x in infer_samples],
    }


def _scenario_estimate(
    *,
    architecture_id: str,
    packs: int,
    probe: dict[str, float],
    swap_probes: int,
    pipeline_sec_per_pack: float | None,
) -> dict[str, Any]:
    attach = float(probe["adapter_attach_sec"])
    infer = float(probe["warm_inference_sec"])
    base = float(probe["base_load_sec"])
    extrap_swaps = max(packs - swap_probes, 0)
    gpu_swap_total_sec = base + attach * packs + infer
    gpu_session_min = round(gpu_swap_total_sec / 60.0, 3)
    row: dict[str, Any] = {
        "architecture_id": architecture_id,
        "packs": packs,
        "swap_probes_measured": swap_probes,
        "mean_adapter_attach_sec": round(attach, 4),
        "warm_inference_sec": round(infer, 4),
        "base_model_load_sec": round(base, 4),
        "gpu_cold_plus_swaps_sec": round(gpu_swap_total_sec, 3),
        "gpu_session_minutes_extrapolated": gpu_session_min,
        "extrapolated_extra_swaps": extrap_swaps,
    }
    if pipeline_sec_per_pack is not None:
        pipeline_total = pipeline_sec_per_pack * packs
        row["pipeline_serial_sec_extrapolated"] = round(pipeline_total, 3)
        row["pipeline_serial_minutes_extrapolated"] = round(pipeline_total / 60.0, 3)
        row["gpu_vs_pipeline_ratio"] = round(gpu_swap_total_sec / pipeline_total, 3) if pipeline_total else None
    return row


def build_ablation(
    *,
    sweep_path: Path,
    extrap_path: Path,
    golden_path: Path,
    profile_path: Path,
    adapter_path: Path,
    profile_key: str,
    max_swap_probes: int,
    max_new_tokens: int,
    dry_run: bool,
) -> dict[str, Any]:
    sweep_doc = _load_json(sweep_path) if sweep_path.is_file() else {}
    extrap_doc = _load_json(extrap_path) if extrap_path.is_file() else {}
    pipeline_sec = (
        float(extrap_doc.get("efficiency_stats", {}).get("mean_pipeline_elapsed_sec_per_pack", 0)) or None
    )

    gpu = _gpu_info()
    adapter_ok = adapter_path.is_dir() and any(adapter_path.glob("adapter_*"))

    report: dict[str, Any] = {
        "schema": "lora_domain_architecture_gpu_ablation_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "gpu": gpu,
        "adapter_path": str(adapter_path),
        "adapter_present": adapter_ok,
        "profile_key": profile_key,
        "max_swap_probes": max_swap_probes,
        "max_new_tokens": max_new_tokens,
        "dry_run": dry_run,
        "sweep_pointer": str(sweep_path),
        "extrapolation_pointer": str(extrap_path),
        "sweep_best_id": sweep_doc.get("verdict", {}).get("best_candidate_id"),
        "hybrid_routing_uplift": sweep_doc.get("hybrid_routing_uplift"),
    }

    if dry_run or not gpu.get("cuda_available") or not adapter_ok:
        report["status"] = "skipped"
        report["skip_reason"] = (
            "dry_run"
            if dry_run
            else ("no_cuda" if not gpu.get("cuda_available") else "adapter_missing")
        )
        report["scenarios"] = [
            _scenario_estimate(
                architecture_id=s["id"],
                packs=int(s["packs"]),
                probe={"base_load_sec": 0.0, "adapter_attach_sec": 0.0, "warm_inference_sec": 0.0},
                swap_probes=0,
                pipeline_sec_per_pack=pipeline_sec,
            )
            for s in ARCHITECTURE_SCENARIOS
        ]
        report["verdict_ko"] = "GPU ablation skipped — dry-run or missing CUDA/adapter."
        return report

    mod = _import_inference_helpers()
    model_name = mod._resolve_profile_model_id(profile_path, profile_key)
    load_in_4bit, bnb_type = mod._resolve_quantization(profile_path)
    instruction = _pick_instruction(golden_path)

    mean_probe = _measure_swap_session(
        model_name=model_name,
        adapter_path=adapter_path,
        instruction=instruction,
        load_in_4bit=load_in_4bit,
        bnb_4bit_quant_type=bnb_type,
        max_new_tokens=max_new_tokens,
        swap_probes=max(1, max_swap_probes),
    )

    scenarios = [
        _scenario_estimate(
            architecture_id=s["id"],
            packs=int(s["packs"]),
            probe=mean_probe,
            swap_probes=max_swap_probes,
            pipeline_sec_per_pack=pipeline_sec,
        )
        for s in ARCHITECTURE_SCENARIOS
    ]

    bench = next(s for s in scenarios if s["architecture_id"] == "bench_4x40")
    hybrid = next(s for s in scenarios if s["architecture_id"] == "hier_12x75_hybrid")
    flat20 = next(s for s in scenarios if s["architecture_id"] == "flat_20x40")

    report.update(
        {
            "status": "ok",
            "model_id": model_name,
            "quantization_4bit": load_in_4bit,
            "measurement_session": mean_probe,
            "scenarios": scenarios,
            "verdict_ko": (
                f"GPU measured attach ~{mean_probe['adapter_attach_sec']:.2f}s, infer ~{mean_probe['warm_inference_sec']:.2f}s. "
                f"bench 4×40 session ~{bench['gpu_session_minutes_extrapolated']} min vs "
                f"12×75 hybrid ~{hybrid['gpu_session_minutes_extrapolated']} min vs "
                f"20-pack ~{flat20['gpu_session_minutes_extrapolated']} min (cold base + N swaps)."
            ),
        }
    )
    return report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LoRA architecture GPU ablation (B-track).")
    p.add_argument("--sweep-json", default=str(DEFAULT_SWEEP))
    p.add_argument("--extrapolation-json", default=str(DEFAULT_EXTRAP))
    p.add_argument("--golden-jsonl", default=str(DEFAULT_GOLDEN))
    p.add_argument("--profile-json", default=str(DEFAULT_PROFILE))
    p.add_argument("--profile-key", default="train_default")
    p.add_argument("--adapter-path", default=str(DEFAULT_ADAPTER))
    p.add_argument("--max-swap-probes", type=int, default=2)
    p.add_argument("--max-new-tokens", type=int, default=96)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_ablation(
        sweep_path=Path(args.sweep_json),
        extrap_path=Path(args.extrapolation_json),
        golden_path=Path(args.golden_jsonl),
        profile_path=Path(args.profile_json),
        adapter_path=Path(args.adapter_path),
        profile_key=str(args.profile_key),
        max_swap_probes=int(args.max_swap_probes),
        max_new_tokens=int(args.max_new_tokens),
        dry_run=bool(args.dry_run),
    )
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out_path), "status": report.get("status"), "skip_reason": report.get("skip_reason")}))
    return 0 if report.get("status") in {"ok", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
