#!/usr/bin/env python3
"""Generate Kaggle notebook with embedded train script (Kaggle only ships .ipynb)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _notebook_cells(
    py_text: str,
    *,
    train_profile: str = "fast",
    kaggle_full: bool = False,
) -> list[dict]:
    lines = py_text.splitlines()
    write_body = ["%%writefile nemotron_qlora_train_v1.py\n"] + [ln + "\n" for ln in lines]
    full_env_lines = (
        ["os.environ['MKM_KAGGLE_FULL'] = '1'\n"] if kaggle_full else []
    )
    return [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Kaggle train (MKM lane: no core, no submit)\n",
                "\n",
                "**Before Run:** Settings → **GPU T4 x2** · Internet ON · **Add-ons → Secrets → `HF_TOKEN`** (Hugging Face read token).\n",
                "\n",
                "| Mode | How | Time |\n",
                "|------|-----|------|\n",
                "| **Tonight (default)** | Just **Save & Run All** — profile `fast`, tiny model, proves zip pipeline | ~15–40 min |\n",
                "| **Nemotron 30B** | Add env `MKM_KAGGLE_TRAIN_PROFILE=nemotron` (or `MKM_KAGGLE_FULL=1`) | 2–4+ h, may fail |\n",
                "\n",
                "- **Do not submit** to competition until human gate\n",
            ],
        },
        {
            "cell_type": "code",
            "metadata": {},
            "source": write_body,
            "outputs": [],
            "execution_count": None,
        },
        {
            "cell_type": "code",
            "metadata": {},
            "source": [
                "import os\n",
                "import runpy\n",
                "import shutil\n",
                "import sys\n",
                "from pathlib import Path\n",
                "\n",
                "pydeps = Path('/kaggle/working/pydeps')\n",
                "if pydeps.is_dir():\n",
                "    shutil.rmtree(pydeps, ignore_errors=True)\n",
                "    print('[cell] wiped stale pydeps')\n",
                "\n",
                "os.environ.pop('PYTHONPATH', None)\n",
                "os.environ['PYTHONUNBUFFERED'] = '1'\n",
                "# HF: Add-ons → Secrets → name HF_TOKEN (do NOT paste token into notebook source)\n",
                "try:\n",
                "    from kaggle_secrets import UserSecretsClient\n",
                "    os.environ['HF_TOKEN'] = UserSecretsClient().get_secret('HF_TOKEN')\n",
                "    print('[cell] HF_TOKEN loaded from Kaggle Secrets')\n",
                "except Exception as exc:\n",
                "    print(f'[cell] WARN: HF_TOKEN secret missing ({exc})')\n",
                "    print('[cell] Kaggle → Add-ons → Secrets → HF_TOKEN → Save → Restart session')\n",
                f"os.environ['MKM_KAGGLE_TRAIN_PROFILE'] = {train_profile!r}\n",
                *full_env_lines,
                "full = os.getenv('MKM_KAGGLE_FULL', '').lower() in ('1', 'true', 'yes')\n",
                "if full:\n",
                "    sys.argv = ['nemotron_qlora_train_v1.py']\n",
                "    mode = 'nemotron FULL (bounded session)'\n",
                "else:\n",
                "    sys.argv = ['nemotron_qlora_train_v1.py', '--smoke']\n",
                "    mode = f\"{os.environ.get('MKM_KAGGLE_TRAIN_PROFILE')} SMOKE\"\n",
                "print('Running in-process:', ' '.join(sys.argv), '|', mode)\n",
                "try:\n",
                "    runpy.run_path('nemotron_qlora_train_v1.py', run_name='__main__')\n",
                "except SystemExit as exc:\n",
                "    if exc.code not in (0, None):\n",
                "        raise\n",
                "    print('[cell] train finished OK (exit 0) — check submission.zip under /kaggle/working/')\n",
            ],
            "outputs": [],
            "execution_count": None,
        },
    ]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--slug", default="nvidia-nemotron-model-reasoning-challenge")
    p.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument(
        "--train-profile",
        choices=("fast", "nemotron"),
        default="fast",
        help="Default Kaggle train profile when not MKM_KAGGLE_FULL",
    )
    p.add_argument(
        "--kaggle-full",
        action="store_true",
        help="Bake MKM_KAGGLE_FULL=1 into run cell (Phase C bounded full)",
    )
    args = p.parse_args()
    root = args.workspace_root
    train_py = root / "data" / "kaggle" / args.slug / "kaggle_train" / "nemotron_qlora_train_v1.py"
    out_ipynb = root / "data" / "kaggle" / args.slug / "kaggle_train_nb" / "nemotron_qlora_train_v1.ipynb"
    if not train_py.is_file():
        raise SystemExit(f"missing {train_py}")

    nb = {
        "cells": _notebook_cells(
            train_py.read_text(encoding="utf-8"),
            train_profile=args.train_profile,
            kaggle_full=args.kaggle_full,
        ),
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    out_ipynb.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] wrote {out_ipynb} ({len(nb['cells'])} cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
