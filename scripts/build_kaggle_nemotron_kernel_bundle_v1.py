#!/usr/bin/env python3
"""Validate Nemotron Kaggle train kernel bundle and emit launch manifest (no push)."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

DEFAULT_SLUG = "nvidia-nemotron-model-reasoning-challenge"


def _now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--slug", default=DEFAULT_SLUG)
    p.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument(
        "--out-json",
        type=Path,
        default=Path("reports/kaggle_nemotron_kernel_bundle_latest.json"),
    )
    args = p.parse_args()
    root = args.workspace_root
    bundle_dir = root / "data" / "kaggle" / args.slug / "kaggle_train"
    nb_bundle_dir = root / "data" / "kaggle" / args.slug / "kaggle_train_nb"
    meta_path = bundle_dir / "kernel-metadata.json"
    py_helper = bundle_dir / "nemotron_qlora_train_v1.py"
    train_csv = root / "data" / "kaggle" / args.slug / "train.csv"

    meta_obj = json.loads(meta_path.read_text(encoding="utf-8"))
    code_file = meta_obj.get("code_file", "nemotron_qlora_train_v1.py")
    code = bundle_dir / code_file

    missing = [str(x) for x in (meta_path, code, py_helper) if not x.is_file()]
    if missing:
        print(f"[ERROR] missing bundle files: {missing}", file=sys.stderr)
        return 1
    if not train_csv.is_file():
        print(f"[ERROR] train.csv not found: {train_csv}", file=sys.stderr)
        return 1

    kernel_id = meta_obj.get("id")
    if not kernel_id:
        print("[ERROR] kernel-metadata.json missing id", file=sys.stderr)
        return 1

    report = {
        "schema": "kaggle_nemotron_kernel_bundle_v1",
        "generated_at_utc": _now_utc(),
        "lane": "private_dev_no_mkm_core",
        "competition_slug": args.slug,
        "bundle_dir": str(bundle_dir.relative_to(root)).replace("\\", "/"),
        "files": {
            "kernel_metadata": {
                "path": str(meta_path.relative_to(root)).replace("\\", "/"),
                "sha256": _sha256(meta_path),
            },
            "notebook_or_script": {
                "path": str(code.relative_to(root)).replace("\\", "/"),
                "sha256": _sha256(code),
            },
            "train_script": {
                "path": str(py_helper.relative_to(root)).replace("\\", "/"),
                "sha256": _sha256(py_helper),
            },
        },
        "kernel_id": kernel_id,
        "kernel_type": meta_obj.get("kernel_type"),
        "enable_gpu": meta_obj.get("enable_gpu"),
        "accelerator": meta_obj.get("accelerator"),
        "competition_sources": meta_obj.get("competition_sources"),
        "train_csv_rows_hint": "9500 (full competition train)",
        "policy": {
            "allow_kernel_push": False,
            "allow_competition_submit": False,
            "push_requires_flag": "AllowKernelPush on Invoke-KaggleNemotronTrainOnKaggle_v1.ps1",
        },
        "launch_steps": [
            "Script v1: https://www.kaggle.com/code/familyunion/nemotron-qlora-private-train-v1",
            "Notebook v2 (preferred): https://www.kaggle.com/code/familyunion/nemotron-qlora-private-train-v2-notebook-t4",
            "Settings → Accelerator → GPU T4 x2 (required; P100 cannot run Nemotron+mamba).",
            "Settings → Internet ON · Private · Add competition data if missing.",
            "Save Version → Run All (smoke default). Full: env MKM_KAGGLE_FULL=1.",
            "Download /kaggle/working/submission.zip; do NOT submit until human gate.",
        ],
        "cli_push_script": f"kaggle kernels push -p {bundle_dir} --accelerator NvidiaTeslaT4",
        "notebook_bundle_dir": str(nb_bundle_dir.relative_to(root)).replace("\\", "/"),
        "notebook_kernel_id": "familyunion/nemotron-qlora-private-train-v2-notebook-t4",
        "cli_push_notebook": f"kaggle kernels push -p {nb_bundle_dir} --accelerator NvidiaTeslaT4",
        "cli_push": f"kaggle kernels push -p {bundle_dir} --accelerator NvidiaTeslaT4",
        "mkm_core_exposed": False,
    }

    out = args.out_json if args.out_json.is_absolute() else root / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote: {out}")
    print(f"[SUMMARY] kernel_id={kernel_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
