#!/usr/bin/env python3
"""Tranche-2 Qwen 7B 4-pack distinct-adapter train ablation (bench_4x40 pack count).

B-track / research_only — measures distinct trained weights + attach latency.
Does not set allow_deploy or multi-pack production GO without human sign-off.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_TRAIN_GOLDEN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl"
DEFAULT_LOCKED_EVAL = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
DEFAULT_PROFILE = ROOT / "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json"
DEFAULT_WORK = ROOT / "reports/lora_tranche2_qwen4pack_v1"
DEFAULT_OUT = ROOT / "reports/lora_tranche2_qwen4pack_train_ablation_latest.json"

BENCH_4X40_PACK_LABELS = ("compression", "governance", "clinical", "market")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _shard_rows_bench4(rows: list[dict[str, Any]], pack_count: int) -> list[list[dict[str, Any]]]:
    buckets: list[list[dict[str, Any]]] = [[] for _ in range(pack_count)]
    for row in rows:
        key = str(row.get("sample_id") or row.get("id") or "")
        idx = hash(key) % pack_count
        buckets[idx].append(row)
    return buckets


def _shard_rows_acode_state(
    rows: list[dict[str, Any]], pack_count: int, registry: dict[str, Any], formulas_doc: dict[str, Any]
) -> tuple[list[list[dict[str, Any]]], str]:
    from scripts.mkm12_acode_pack_router_v1 import route_golden_row_to_pack

    buckets: list[list[dict[str, Any]]] = [[] for _ in range(pack_count)]
    for row in rows:
        routed = route_golden_row_to_pack(row, registry=registry, formulas_doc=formulas_doc)
        pack_id = int(routed["pack_id"])
        if pack_id < 1 or pack_id > pack_count:
            pack_id = ((pack_id - 1) % pack_count) + 1
        buckets[pack_id - 1].append(row)
    return buckets, "acode_state_deterministic_v1"


def _acode_pack_labels(registry: dict[str, Any], pack_count: int) -> list[str]:
    from scripts.mkm12_acode_pack_router_v1 import pack_label_from_registry

    labels: list[str] = []
    for pack_id in range(1, pack_count + 1):
        labels.append(pack_label_from_registry(registry, pack_id))
    return labels


def _load_acode_registry_and_formulas() -> tuple[dict[str, Any], dict[str, Any]]:
    from scripts.mkm12_acode_pack_router_v1 import DEFAULT_FORMULAS, DEFAULT_REGISTRY, load_json

    return load_json(DEFAULT_REGISTRY), load_json(DEFAULT_FORMULAS)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str]) -> int:
    print("[qwen4pack] " + " ".join(cmd))
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def _resolve_profile(profile_json: Path, key: str) -> dict[str, Any]:
    doc = json.loads(profile_json.read_text(encoding="utf-8"))
    prof = (doc.get("profiles") or {}).get(key) or {}
    return prof if isinstance(prof, dict) else {}


def _import_inference_helpers():
    path = ROOT / "scripts/run_myeongri_deterministic_lora_inference_eval_v1.py"
    spec = importlib.util.spec_from_file_location("myeongri_lora_infer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import inference helpers from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _measure_trained_attaches(
    *,
    profile_path: Path,
    profile_key: str,
    adapter_paths: list[Path],
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run or not adapter_paths:
        return {
            "status": "skipped",
            "base_load_sec": 0.0,
            "attach_samples_sec": [],
            "mean_attach_sec": 0.0,
            "total_attach_sec": 0.0,
        }

    mod = _import_inference_helpers()
    import torch
    from peft import PeftModel

    model_name = mod._resolve_profile_model_id(profile_path, profile_key)
    load_in_4bit, bnb_type = mod._resolve_quantization(profile_path)

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
        if not (adapter_path / "adapter_model.safetensors").is_file():
            continue
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
        "status": "ok" if attach_samples else "skipped",
        "base_load_sec": round(base_load_sec, 4),
        "attach_samples_sec": [round(x, 4) for x in attach_samples],
        "mean_attach_sec": round(statistics.mean(attach_samples), 4) if attach_samples else 0.0,
        "total_attach_sec": round(sum(attach_samples), 4),
        "pack_count_measured": len(attach_samples),
    }


def _train_pack(
    *,
    golden_path: Path,
    sft_path: Path,
    adapter_out: Path,
    profile: dict[str, Any],
    train_steps: int,
    max_seq_length: int,
    dry_run: bool,
) -> int:
    convert = [
        sys.executable,
        str(ROOT / "scripts/convert_myeongri_golden_to_sft_instruction_jsonl_v1.py"),
        "--input-jsonl",
        str(golden_path),
        "--output-jsonl",
        str(sft_path),
    ]
    if _run(convert) != 0:
        return 1

    train = [
        sys.executable,
        str(ROOT / "scripts/train_mkm_prophecy_lora_windows_fallback_v1.py"),
        "--dataset-path",
        str(sft_path),
        "--model-name",
        str(profile.get("model_id", "Qwen/Qwen2.5-7B-Instruct")),
        "--max-seq-length",
        str(max_seq_length),
        "--max-steps",
        str(train_steps),
        "--batch-size",
        str(int(profile.get("batch_size", 1))),
        "--grad-accum",
        str(int(profile.get("grad_accum", 8))),
        "--learning-rate",
        str(float(profile.get("learning_rate", 0.0001))),
        "--lora-r",
        str(int(profile.get("lora_r", 16))),
        "--lora-alpha",
        str(int(profile.get("lora_alpha", 32))),
        "--lora-dropout",
        str(float(profile.get("lora_dropout", 0.05))),
        "--output-dir",
        str(adapter_out),
    ]
    if dry_run:
        train.append("--dry-run")
    return _run(train)


def _eval_pack(
    *,
    adapter_out: Path,
    locked_eval: Path,
    profile_key: str,
    report_path: Path,
    pred_path: Path,
    limit: int,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_myeongri_deterministic_lora_inference_eval_v1.py"),
        "--golden-jsonl",
        str(locked_eval),
        "--adapter-path",
        str(adapter_out),
        "--profile-key",
        profile_key,
        "--predictions-jsonl",
        str(pred_path),
        "--report-json",
        str(report_path),
        "--limit",
        str(limit),
        "--split",
        "locked_eval",
    ]
    rc = _run(cmd)
    doc: dict[str, Any] = {}
    if report_path.is_file():
        doc = json.loads(report_path.read_text(encoding="utf-8"))
    return {"exit_code": rc, "report": doc}


def build_ablation(
    *,
    train_golden: Path,
    locked_eval: Path,
    profile_json: Path,
    profile_key: str,
    work_root: Path,
    pack_count: int,
    rows_per_pack_cap: int,
    train_steps: int,
    max_seq_length: int,
    eval_limit: int,
    dry_run: bool,
    architecture_target: str = "bench_4x40",
    skip_if_adapter: bool = False,
    skip_if_eval_report: bool = False,
    shard_mode: str = "hash_sample_id_mod",
) -> dict[str, Any]:
    profile = _resolve_profile(profile_json, profile_key)
    all_rows = _load_jsonl(train_golden)

    acode_registry: dict[str, Any] | None = None
    acode_formulas: dict[str, Any] | None = None
    pack_labels: list[str] | None = None
    effective_shard_mode = f"hash_sample_id_mod_{pack_count}"

    if shard_mode == "acode_state_deterministic_v1":
        if pack_count != 12:
            raise ValueError("acode_state_deterministic_v1 requires --pack-count 12")
        acode_registry, acode_formulas = _load_acode_registry_and_formulas()
        shards, effective_shard_mode = _shard_rows_acode_state(
            all_rows, pack_count, acode_registry, acode_formulas
        )
        pack_labels = _acode_pack_labels(acode_registry, pack_count)
    else:
        shards = _shard_rows_bench4(all_rows, pack_count)

    for i, shard in enumerate(shards):
        if rows_per_pack_cap > 0:
            shards[i] = shard[:rows_per_pack_cap]

    pack_results: list[dict[str, Any]] = []
    adapter_paths: list[Path] = []

    for i in range(pack_count):
        pack_id = i + 1
        if pack_labels is not None:
            label = pack_labels[i]
        elif i < len(BENCH_4X40_PACK_LABELS):
            label = BENCH_4X40_PACK_LABELS[i]
        else:
            label = f"pack_{pack_id}"
        pack_dir = work_root / f"pack_{pack_id:02d}_{label}"
        golden_path = pack_dir / "golden_train.jsonl"
        sft_path = pack_dir / "sft_train.jsonl"
        adapter_out = pack_dir / "adapter"
        eval_report = pack_dir / "locked_eval_report.json"
        pred_path = pack_dir / "locked_eval_predictions.jsonl"

        rows = shards[i]
        _write_jsonl(golden_path, rows)

        train_rc = 0
        adapter_file = adapter_out / "adapter_model.safetensors"
        if skip_if_adapter and adapter_file.is_file() and not dry_run:
            train_rc = 0
        elif rows:
            train_rc = _train_pack(
                golden_path=golden_path,
                sft_path=sft_path,
                adapter_out=adapter_out,
                profile=profile,
                train_steps=train_steps,
                max_seq_length=max_seq_length,
                dry_run=dry_run,
            )

        if not adapter_file.is_file():
            adapter_file = adapter_out / "adapter_model.safetensors"
        weight_sha = _sha256_file(adapter_file) if adapter_file.is_file() else None
        if adapter_out.is_dir() and weight_sha:
            adapter_paths.append(adapter_out)

        eval_doc: dict[str, Any] = {"skipped": True}
        if weight_sha and not dry_run and train_rc == 0:
            if skip_if_eval_report and eval_report.is_file():
                eval_doc = {
                    "exit_code": 0,
                    "report": json.loads(eval_report.read_text(encoding="utf-8")),
                    "reused_report": True,
                }
            else:
                eval_doc = _eval_pack(
                    adapter_out=adapter_out,
                    locked_eval=locked_eval,
                    profile_key=profile_key,
                    report_path=eval_report,
                    pred_path=pred_path,
                    limit=eval_limit,
                )

        pack_entry: dict[str, Any] = {
                "pack_id": pack_id,
                "bench_4x40_label": label,
                "shard_mode": effective_shard_mode,
                "train_rows": len(rows),
                "train_exit_code": train_rc,
                "adapter_dir": str(adapter_out),
                "adapter_weight_sha256": weight_sha,
                "locked_eval": eval_doc,
            }
        if acode_registry is not None:
            pack_entry["acode_state_id"] = next(
                p["acode_state_id"]
                for p in acode_registry["packs"]
                if int(p["pack_id"]) == pack_id
            )
        pack_results.append(pack_entry)

    distinct_hashes = {p["adapter_weight_sha256"] for p in pack_results if p.get("adapter_weight_sha256")}
    trained_count = len(distinct_hashes)
    if dry_run:
        diversity_ok = None
    elif pack_count <= 4:
        diversity_ok = trained_count >= max(2, min(4, pack_count))
    else:
        diversity_ok = trained_count >= pack_count

    attach = _measure_trained_attaches(
        profile_path=profile_json,
        profile_key=profile_key,
        adapter_paths=adapter_paths,
        dry_run=dry_run,
    )

    schema = (
        "lora_tranche2_qwen4pack_train_ablation_v1"
        if pack_count == 4
        else f"lora_tranche2_qwen{pack_count}pack_train_ablation_v1"
    )

    return {
        "schema": schema,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "architecture_target": architecture_target,
        "profile_key": profile_key,
        "model_id": profile.get("model_id"),
        "train_steps": train_steps,
        "max_seq_length": max_seq_length,
        "pack_count": pack_count,
        "shard_mode": effective_shard_mode,
        "dry_run": dry_run,
        "packs": pack_results,
        "diversity": {
            "distinct_weight_hashes": len(distinct_hashes),
            "diversity_ok": diversity_ok,
            "hashes": sorted(distinct_hashes),
        },
        "trained_adapter_attach": attach,
        "verdict_ko": (
            f"Qwen {pack_count}-pack train ablation ({architecture_target}): "
            + (
                f"{len(distinct_hashes)} distinct adapter hashes; attach total "
                f"{attach.get('total_attach_sec', 0)}s."
                if not dry_run
                else "dry-run only (no weights)."
            )
            + " B-track only — not Track A·live-trading GO."
        ),
        "multi_pack_production_go": False,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tranche-2 Qwen multipack train ablation.")
    p.add_argument("--train-golden", default=str(DEFAULT_TRAIN_GOLDEN))
    p.add_argument("--locked-eval", default=str(DEFAULT_LOCKED_EVAL))
    p.add_argument("--profile-json", default=str(DEFAULT_PROFILE))
    p.add_argument("--profile-key", default="train_default")
    p.add_argument("--work-root", default=str(DEFAULT_WORK))
    p.add_argument("--pack-count", type=int, default=4)
    p.add_argument("--architecture-target", default="bench_4x40")
    p.add_argument(
        "--shard-mode",
        default="hash_sample_id_mod",
        choices=["hash_sample_id_mod", "acode_state_deterministic_v1"],
        help="hash_sample_id_mod (default) or acode_state_deterministic_v1 (12-pack MKM12 lane).",
    )
    p.add_argument("--rows-per-pack-cap", type=int, default=60)
    p.add_argument("--train-steps", type=int, default=12)
    p.add_argument("--max-seq-length", type=int, default=512)
    p.add_argument("--eval-limit", type=int, default=2)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--skip-if-adapter",
        action="store_true",
        help="Reuse pack adapter when adapter_model.safetensors exists (resume).",
    )
    p.add_argument(
        "--skip-if-eval-report",
        action="store_true",
        help="Reuse locked_eval_report.json when present (resume).",
    )
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    report = build_ablation(
        train_golden=Path(args.train_golden),
        locked_eval=Path(args.locked_eval),
        profile_json=Path(args.profile_json),
        profile_key=str(args.profile_key),
        work_root=Path(args.work_root),
        pack_count=int(args.pack_count),
        rows_per_pack_cap=int(args.rows_per_pack_cap),
        train_steps=int(args.train_steps),
        max_seq_length=int(args.max_seq_length),
        eval_limit=int(args.eval_limit),
        dry_run=bool(args.dry_run),
        architecture_target=str(args.architecture_target),
        skip_if_adapter=bool(args.skip_if_adapter),
        skip_if_eval_report=bool(args.skip_if_eval_report),
        shard_mode=str(args.shard_mode),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out_path),
                "diversity_ok": report["diversity"].get("diversity_ok"),
                "attach_total_sec": report["trained_adapter_attach"].get("total_attach_sec"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
