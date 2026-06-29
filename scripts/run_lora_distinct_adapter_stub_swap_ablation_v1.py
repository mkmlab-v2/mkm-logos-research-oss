#!/usr/bin/env python3
"""Distinct adapter-path swap ablation (stub copies, no new training).

Copies the SSOT Pack 0-B adapter into N separate directories and measures
Peft attach latency per path. B-track / research_only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_ADAPTER = (
    ROOT / "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_train_default_completion"
)
DEFAULT_PROFILE = ROOT / "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json"
DEFAULT_STUB_ROOT = ROOT / "reports/lora_stub_adapters_v1"
DEFAULT_OUT = ROOT / "reports/lora_distinct_adapter_stub_swap_ablation_latest.json"

SCENARIOS = (
    {"architecture_id": "bench_4x40", "packs": 4},
    {"architecture_id": "hier_12x75_hybrid", "packs": 12},
    {"architecture_id": "flat_20x40", "packs": 20},
)

STUB_FILES = ("adapter_config.json", "adapter_model.safetensors")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _import_inference_helpers():
    path = ROOT / "scripts/run_myeongri_deterministic_lora_inference_eval_v1.py"
    spec = importlib.util.spec_from_file_location("myeongri_lora_infer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _link_or_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    if src.suffix == ".safetensors":
        try:
            os.link(src, dest)
            return
        except OSError:
            pass
    shutil.copy2(src, dest)


def _ensure_stub_adapters(*, source: Path, stub_root: Path, count: int, refresh: bool) -> list[Path]:
    if refresh and stub_root.is_dir():
        shutil.rmtree(stub_root)
    stub_root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i in range(1, count + 1):
        dest = stub_root / f"pack_{i:03d}"
        dest.mkdir(parents=True, exist_ok=True)
        for name in STUB_FILES:
            _link_or_copy(source / name, dest / name)
        paths.append(dest)
    return paths


def _measure_distinct_attaches(
    *,
    model_name: str,
    adapter_paths: list[Path],
    load_in_4bit: bool,
    bnb_type: str,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "base_load_sec": 0.0,
            "attach_samples_sec": [0.0] * len(adapter_paths),
            "mean_attach_sec": 0.0,
            "total_attach_sec": 0.0,
        }

    mod = _import_inference_helpers()
    import torch
    from peft import PeftModel

    t0 = time.perf_counter()
    base_model, tokenizer = mod._load_model_and_tokenizer(
        model_name,
        "",
        load_in_4bit=load_in_4bit,
        bnb_4bit_quant_type=bnb_type,
    )
    base_load_sec = time.perf_counter() - t0
    del tokenizer

    attach_samples: list[float] = []
    for adapter_path in adapter_paths:
        t_a0 = time.perf_counter()
        model = PeftModel.from_pretrained(base_model, str(adapter_path))
        model.eval()
        attach_samples.append(time.perf_counter() - t_a0)
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    del base_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return {
        "base_load_sec": round(base_load_sec, 4),
        "attach_samples_sec": [round(x, 4) for x in attach_samples],
        "mean_attach_sec": round(statistics.mean(attach_samples), 4) if attach_samples else 0.0,
        "total_attach_sec": round(sum(attach_samples), 4),
    }


def build_report(
    *,
    source_adapter: Path,
    stub_root: Path,
    profile_path: Path,
    profile_key: str,
    max_packs: int,
    refresh_stubs: bool,
    dry_run: bool,
) -> dict[str, Any]:
    mod = _import_inference_helpers()
    gpu: dict[str, Any] = {"cuda_available": False}
    try:
        import torch

        gpu["cuda_available"] = bool(torch.cuda.is_available())
        if gpu["cuda_available"]:
            gpu["device_name"] = torch.cuda.get_device_name(0)
    except Exception as exc:
        gpu["error"] = str(exc)

    adapter_ok = source_adapter.is_dir() and (source_adapter / "adapter_model.safetensors").is_file()
    report: dict[str, Any] = {
        "schema": "lora_distinct_adapter_stub_swap_ablation_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "note": "Stub adapters are byte-identical copies; measures path-distinct attach only, not training diversity.",
        "source_adapter": str(source_adapter),
        "stub_root": str(stub_root),
        "gpu": gpu,
        "dry_run": dry_run,
    }

    if dry_run or not gpu.get("cuda_available") or not adapter_ok:
        report["status"] = "skipped"
        report["skip_reason"] = (
            "dry_run" if dry_run else ("no_cuda" if not gpu.get("cuda_available") else "adapter_missing")
        )
        report["scenarios"] = [
            {
                "architecture_id": s["architecture_id"],
                "packs": s["packs"],
                "mean_attach_sec": 0.0,
                "total_attach_sec": 0.0,
            }
            for s in SCENARIOS
            if int(s["packs"]) <= max_packs
        ]
        return report

    model_name = mod._resolve_profile_model_id(profile_path, profile_key)
    load_in_4bit, bnb_type = mod._resolve_quantization(profile_path)
    max_n = max(int(s["packs"]) for s in SCENARIOS if int(s["packs"]) <= max_packs)
    stub_paths = _ensure_stub_adapters(
        source=source_adapter,
        stub_root=stub_root,
        count=max_n,
        refresh=refresh_stubs,
    )

    full_measurement = _measure_distinct_attaches(
        model_name=model_name,
        adapter_paths=stub_paths,
        load_in_4bit=load_in_4bit,
        bnb_type=bnb_type,
        dry_run=False,
    )
    attach_samples = list(full_measurement.get("attach_samples_sec") or [])

    scenario_rows: list[dict[str, Any]] = []
    for spec in SCENARIOS:
        n = int(spec["packs"])
        if n > max_packs:
            continue
        samples = attach_samples[:n]
        total_attach = round(sum(float(x) for x in samples), 4)
        mean_attach = round(statistics.mean(samples), 4) if samples else 0.0
        scenario_rows.append(
            {
                "architecture_id": spec["architecture_id"],
                "packs": n,
                "stub_paths_used": [str(p) for p in stub_paths[:n]],
                "base_load_sec": full_measurement["base_load_sec"],
                "attach_samples_sec": samples,
                "mean_attach_sec": mean_attach,
                "total_attach_sec": total_attach,
                "session_sec_with_base": round(
                    float(full_measurement["base_load_sec"]) + total_attach,
                    4,
                ),
            }
        )

    bench = next(r for r in scenario_rows if r["architecture_id"] == "bench_4x40")
    hybrid = next(r for r in scenario_rows if r["architecture_id"] == "hier_12x75_hybrid")
    flat20 = next(r for r in scenario_rows if r["architecture_id"] == "flat_20x40")

    report.update(
        {
            "status": "ok",
            "model_id": model_name,
            "stub_count_prepared": len(stub_paths),
            "scenarios": scenario_rows,
            "verdict_ko": (
                f"Distinct-path attach (identical weights): 4-pack total attach {bench['total_attach_sec']:.2f}s, "
                f"12-pack {hybrid['total_attach_sec']:.2f}s, 20-pack {flat20['total_attach_sec']:.2f}s. "
                "Training diversity not measured."
            ),
        }
    )
    return report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Distinct adapter stub swap ablation.")
    p.add_argument("--source-adapter", default=str(DEFAULT_ADAPTER))
    p.add_argument("--stub-root", default=str(DEFAULT_STUB_ROOT))
    p.add_argument("--profile-json", default=str(DEFAULT_PROFILE))
    p.add_argument("--profile-key", default="train_default")
    p.add_argument("--max-packs", type=int, default=20)
    p.add_argument("--refresh-stubs", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_report(
        source_adapter=Path(args.source_adapter),
        stub_root=Path(args.stub_root),
        profile_path=Path(args.profile_json),
        profile_key=str(args.profile_key),
        max_packs=int(args.max_packs),
        refresh_stubs=bool(args.refresh_stubs),
        dry_run=bool(args.dry_run),
    )
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out_path), "status": report.get("status")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
