#!/usr/bin/env python3
"""Tranche-2 micro-train diversity probe: 3 TinyLlama LoRA packs on data shards.

B-track / research_only — distinct weights check via SHA256; not multi-pack production GO.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_TRAIN_GOLDEN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl"
DEFAULT_LOCKED_EVAL = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
DEFAULT_PROFILE = ROOT / "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json"
DEFAULT_WORK = ROOT / "reports/lora_tranche2_microtrain_v1"
DEFAULT_OUT = ROOT / "reports/lora_tranche2_microtrain_diversity_probe_latest.json"


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


def _shard_rows(rows: list[dict[str, Any]], packs: int) -> list[list[dict[str, Any]]]:
    buckets: list[list[dict[str, Any]]] = [[] for _ in range(packs)]
    for row in rows:
        key = str(row.get("sample_id") or row.get("id") or "")
        idx = hash(key) % packs
        buckets[idx].append(row)
    return buckets


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str]) -> int:
    print("[microtrain] " + " ".join(cmd))
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def _resolve_profile(profile_json: Path, key: str) -> dict[str, Any]:
    doc = json.loads(profile_json.read_text(encoding="utf-8"))
    prof = (doc.get("profiles") or {}).get(key) or {}
    return prof if isinstance(prof, dict) else {}


def _train_pack(
    *,
    pack_id: int,
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
        str(profile.get("model_id", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")),
        "--max-seq-length",
        str(max_seq_length),
        "--max-steps",
        str(train_steps),
        "--batch-size",
        str(int(profile.get("batch_size", 1))),
        "--grad-accum",
        str(int(profile.get("grad_accum", 4))),
        "--learning-rate",
        str(float(profile.get("learning_rate", 0.00015))),
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
    pack_id: int,
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


def build_probe(
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
) -> dict[str, Any]:
    profile = _resolve_profile(profile_json, profile_key)
    all_rows = _load_jsonl(train_golden)
    shards = _shard_rows(all_rows, pack_count)
    for i, shard in enumerate(shards):
        if rows_per_pack_cap > 0:
            shards[i] = shard[:rows_per_pack_cap]

    pack_results: list[dict[str, Any]] = []
    for i in range(pack_count):
        pack_id = i + 1
        pack_dir = work_root / f"pack_{pack_id:02d}"
        golden_path = pack_dir / "golden_train.jsonl"
        sft_path = pack_dir / "sft_train.jsonl"
        adapter_out = pack_dir / "adapter"
        eval_report = pack_dir / "locked_eval_report.json"
        pred_path = pack_dir / "locked_eval_predictions.jsonl"

        rows = shards[i]
        _write_jsonl(golden_path, rows)

        train_rc = 0
        if rows and not dry_run:
            train_rc = _train_pack(
                pack_id=pack_id,
                golden_path=golden_path,
                sft_path=sft_path,
                adapter_out=adapter_out,
                profile=profile,
                train_steps=train_steps,
                max_seq_length=max_seq_length,
                dry_run=dry_run,
            )
        elif dry_run:
            train_rc = _train_pack(
                pack_id=pack_id,
                golden_path=golden_path,
                sft_path=sft_path,
                adapter_out=adapter_out,
                profile=profile,
                train_steps=train_steps,
                max_seq_length=max_seq_length,
                dry_run=True,
            )

        adapter_file = adapter_out / "adapter_model.safetensors"
        weight_sha = _sha256_file(adapter_file) if adapter_file.is_file() else None

        eval_doc: dict[str, Any] = {"skipped": True}
        if weight_sha and not dry_run and train_rc == 0:
            eval_doc = _eval_pack(
                pack_id=pack_id,
                adapter_out=adapter_out,
                locked_eval=locked_eval,
                profile_key=profile_key,
                report_path=eval_report,
                pred_path=pred_path,
                limit=eval_limit,
            )

        pack_results.append(
            {
                "pack_id": pack_id,
                "train_rows": len(rows),
                "train_exit_code": train_rc,
                "adapter_dir": str(adapter_out),
                "adapter_weight_sha256": weight_sha,
                "locked_eval": eval_doc,
            }
        )

    distinct_hashes = {p["adapter_weight_sha256"] for p in pack_results if p.get("adapter_weight_sha256")}
    diversity_ok = len(distinct_hashes) >= 2 if not dry_run else None

    return {
        "schema": "lora_tranche2_microtrain_diversity_probe_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "profile_key": profile_key,
        "model_id": profile.get("model_id"),
        "train_steps": train_steps,
        "max_seq_length": max_seq_length,
        "pack_count": pack_count,
        "dry_run": dry_run,
        "packs": pack_results,
        "diversity": {
            "distinct_weight_hashes": len(distinct_hashes),
            "diversity_ok": diversity_ok,
            "hashes": sorted(distinct_hashes),
        },
        "verdict_ko": (
            "Micro-train diversity probe: "
            + (
                f"{len(distinct_hashes)} distinct adapter hashes across {pack_count} packs."
                if not dry_run
                else "dry-run only (no weights)."
            )
            + " Not a production multi-pack GO."
        ),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tranche-2 micro-train diversity probe (3-pack TinyLlama).")
    p.add_argument("--train-golden", default=str(DEFAULT_TRAIN_GOLDEN))
    p.add_argument("--locked-eval", default=str(DEFAULT_LOCKED_EVAL))
    p.add_argument("--profile-json", default=str(DEFAULT_PROFILE))
    p.add_argument("--profile-key", default="golden_fit_smoke")
    p.add_argument("--work-root", default=str(DEFAULT_WORK))
    p.add_argument("--pack-count", type=int, default=3)
    p.add_argument("--rows-per-pack-cap", type=int, default=80)
    p.add_argument("--train-steps", type=int, default=12)
    p.add_argument("--max-seq-length", type=int, default=512)
    p.add_argument("--eval-limit", type=int, default=2)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    report = build_probe(
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
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out_path), "diversity_ok": report["diversity"].get("diversity_ok")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
