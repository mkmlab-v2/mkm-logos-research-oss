#!/usr/bin/env python3
"""Build single Kaggle cell: materialize train script + nemotron smoke runner."""

from __future__ import annotations

import base64
import textwrap
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "kaggle" / "nvidia-nemotron-model-reasoning-challenge" / "kaggle_train" / "nemotron_qlora_train_v1.py"
SRC_WRITEFILE = ROOT / "reports" / "kaggle_nemotron_notebook_cell1_writefile_v46.txt"
CELL2 = ROOT / "reports" / "kaggle_nemotron_notebook_cell2_run_nemotron_smoke_v1.txt"
OUT = ROOT / "reports" / "kaggle_nemotron_notebook_cell12_combined_v46.txt"

RUNNER_HEADER = '''# MKM Kaggle — Cell 1+2 combined v46 (code cell 하나만 · Run)
# Settings: GPU T4 x2 · Internet ON · Secrets: HF_TOKEN (권장)

import base64
import os
import runpy
import shutil
import sys
import zlib
from pathlib import Path

_NEMOTRON_TRAIN_B85 = (
'''

RUNNER_FOOTER = '''
)

Path("nemotron_qlora_train_v1.py").write_bytes(
    zlib.decompress(base64.b85decode(_NEMOTRON_TRAIN_B85.encode("ascii")))
)
print("[combined] wrote nemotron_qlora_train_v1.py")

'''

CELL2_BODY = '''
for _p in (
    "/kaggle/tmp/hf_hub",
    "/kaggle/tmp/accelerate_offload",
    "/root/.cache/huggingface",
    "/kaggle/working/mamba_wheels",
):
    shutil.rmtree(_p, ignore_errors=True)
    print("[cell] cleared", _p)
# Keep /kaggle/tmp/nemotron_hf_model if present (63GB re-download skip on retry)

import gc
gc.collect()
print("[cell] gc after cache purge")

for _n in list(sys.modules):
    if _n == "torchvision" or _n.startswith("torchvision."):
        sys.modules.pop(_n, None)

pydeps = Path("/kaggle/working/pydeps")
if pydeps.is_dir():
    shutil.rmtree(pydeps, ignore_errors=True)
    print("[cell] wiped stale pydeps")

os.environ.pop("PYTHONPATH", None)
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
try:
    from kaggle_secrets import UserSecretsClient

    os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
    print("[cell] HF_TOKEN loaded from Kaggle Secrets")
except Exception as exc:
    print(f"[cell] WARN: HF_TOKEN secret missing ({exc})")

os.environ["MKM_KAGGLE_TRAIN_PROFILE"] = "nemotron"
sys.argv = ["nemotron_qlora_train_v1.py", "--smoke"]
print("Running in-process:", " ".join(sys.argv), "| profile=nemotron SMOKE (30B short)")
try:
    runpy.run_path("nemotron_qlora_train_v1.py", run_name="__main__")
except SystemExit as exc:
    if exc.code not in (0, None):
        raise
    print("[cell] nemotron smoke finished OK (exit 0)")
'''


def _load_script() -> str:
    raw = SRC.read_text(encoding="utf-8")
    if not raw.endswith("\n"):
        raw += "\n"
    SRC_WRITEFILE.write_text(
        "%%writefile nemotron_qlora_train_v1.py\n" + raw,
        encoding="utf-8",
    )
    return raw


def _chunk_b85(blob: str, width: int = 76) -> str:
    lines = textwrap.wrap(blob, width=width)
    if not lines:
        return '    ""\n'
    out = [f'    "{lines[0]}"']
    for line in lines[1:]:
        out.append(f'    "{line}"')
    return "\n".join(out) + "\n"


def main() -> None:
    script = _load_script()
    b85 = base64.b85encode(zlib.compress(script.encode("utf-8"), 9)).decode("ascii")
    parts = [RUNNER_HEADER, _chunk_b85(b85), RUNNER_FOOTER, CELL2_BODY]
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"[OK] {OUT} ({len(OUT.read_text(encoding='utf-8').splitlines())} lines)")


if __name__ == "__main__":
    main()
