#!/usr/bin/env python3
"""Logos edge-hypothesis local micro-train ([HYPO] B-track, research_only).

Wires logos_edge_hypothesis_sft_v1_latest.jsonl → train_mkm_prophecy_lora_windows_fallback_v1.py
(TinyLlama smoke by default). No canonical merge · no showroom · no live trading.
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
DEFAULT_JSONL = ROOT / "docs/final/artifacts/logos_edge_hypothesis_sft_v1_latest.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_edge_hypothesis_sft_manifest_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_edge_hypothesis_microtrain_v1"
DEFAULT_REPORT = ROOT / "reports/logos_edge_hypothesis_microtrain_v1_latest.json"
TRAIN_SCRIPT = ROOT / "scripts/train_mkm_prophecy_lora_windows_fallback_v1.py"
DEFAULT_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if "instruction" not in obj or "output" not in obj:
            raise ValueError(f"line {i}: expected instruction/output")
        rows.append(obj)
    return rows


def _check_deps() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for mod in ("torch", "transformers", "peft", "datasets"):
        try:
            m = __import__(mod)
            out[mod] = {"ok": True, "version": getattr(m, "__version__", None)}
        except Exception as exc:
            out[mod] = {"ok": False, "error": str(exc)}
    if out.get("torch", {}).get("ok"):
        import torch

        out["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            out["cuda_device"] = torch.cuda.get_device_name(0)
    return out


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _validate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hypo_rows = sum(1 for r in rows if "[HYPO]" in str(r.get("output", "")))
    meta_ok = sum(
        1
        for r in rows
        if isinstance(r.get("metadata"), dict)
        and r["metadata"].get("merge_to_canonical_allowed") is False
    )
    return {
        "row_count": len(rows),
        "hypo_tag_rows": hypo_rows,
        "metadata_wall_rows": meta_ok,
        "contract_ok": len(rows) > 0 and hypo_rows == len(rows) and meta_ok == len(rows),
    }


def _run_train(
    *,
    jsonl: Path,
    adapter_out: Path,
    model_name: str,
    max_steps: int,
    max_seq_length: int,
    dry_run: bool,
) -> int:
    cmd = [
        sys.executable,
        str(TRAIN_SCRIPT),
        "--dataset-path",
        str(jsonl),
        "--output-dir",
        str(adapter_out),
        "--model-name",
        model_name,
        "--max-seq-length",
        str(max_seq_length),
        "--max-steps",
        str(max_steps),
        "--batch-size",
        "1",
        "--grad-accum",
        "2",
        "--learning-rate",
        "0.00015",
        "--lora-r",
        "8",
        "--lora-alpha",
        "16",
        "--lora-dropout",
        "0.05",
    ]
    if dry_run:
        cmd.append("--dry-run")
    print("[microtrain] " + " ".join(cmd))
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def build_report(
    *,
    jsonl: Path,
    manifest: Path,
    adapter_out: Path,
    model_name: str,
    max_steps: int,
    mode: str,
    train_exit: int,
    validation: dict[str, Any],
    deps: dict[str, Any],
) -> dict[str, Any]:
    adapter_config = adapter_out / "adapter_config.json"
    adapter_saved = adapter_config.is_file()
    smoke_ok = mode == "dry_run" and train_exit == 0
    if mode == "smoke":
        smoke_ok = train_exit == 0 and adapter_saved and deps.get("cuda_available") is True

    return {
        "schema": "logos_edge_hypothesis_microtrain_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "kaggle_lane": False,
        "mode": mode,
        "model_name": model_name,
        "max_steps": max_steps,
        "dataset_jsonl": _rel(jsonl),
        "manifest_json": _rel(manifest) if manifest.is_file() else None,
        "adapter_out": _rel(adapter_out),
        "adapter_saved": adapter_saved,
        "validation": validation,
        "dependencies": deps,
        "train_exit_code": train_exit,
        "microtrain_smoke_ok": smoke_ok,
        "showroom_live_trading_auto_merge": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--adapter-out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--model-name", default=DEFAULT_MODEL)
    ap.add_argument("--max-steps", type=int, default=8)
    ap.add_argument("--max-seq-length", type=int, default=512)
    ap.add_argument(
        "--mode",
        choices=("dry_run", "smoke"),
        default="dry_run",
        help="dry_run=parse+deps only; smoke=TinyLlama LoRA micro-train (GPU)",
    )
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing jsonl: {args.jsonl}"}))
        return 1
    if not TRAIN_SCRIPT.is_file():
        print(json.dumps({"ok": False, "error": f"missing train script: {TRAIN_SCRIPT}"}))
        return 1

    rows = _load_jsonl(args.jsonl)
    validation = _validate_rows(rows)
    if not validation["contract_ok"]:
        print(json.dumps({"ok": False, "error": "SFT contract failed", "validation": validation}))
        return 1

    deps = _check_deps()
    if args.mode == "smoke" and not deps.get("cuda_available"):
        print(json.dumps({"ok": False, "error": "CUDA required for smoke mode", "dependencies": deps}))
        return 1

    train_exit = _run_train(
        jsonl=args.jsonl,
        adapter_out=args.adapter_out,
        model_name=args.model_name,
        max_steps=args.max_steps,
        max_seq_length=args.max_seq_length,
        dry_run=(args.mode == "dry_run"),
    )

    report = build_report(
        jsonl=args.jsonl,
        manifest=args.manifest_json,
        adapter_out=args.adapter_out,
        model_name=args.model_name,
        max_steps=args.max_steps,
        mode=args.mode,
        train_exit=train_exit,
        validation=validation,
        deps=deps,
    )
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.manifest_json.is_file():
        manifest = json.loads(args.manifest_json.read_text(encoding="utf-8-sig"))
        if report["microtrain_smoke_ok"]:
            manifest["train_entry_mode"] = "microtrain_smoke_ok"
            manifest["microtrain_report"] = _rel(args.report_json)
            manifest["microtrain_at_utc"] = report["generated_at_utc"]
            args.manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": report["microtrain_smoke_ok"], "report": _rel(args.report_json), **report}))
    return 0 if report["microtrain_smoke_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
