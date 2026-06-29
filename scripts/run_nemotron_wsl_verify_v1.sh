#!/usr/bin/env bash
set -euo pipefail
PY="${1:-/mnt/c/workspace/.venv-wsl-nemotron/bin/python}"
"$PY" - <<'PY'
import importlib
for m in ("torch", "transformers", "peft", "trl", "bitsandbytes", "mamba_ssm", "datasets", "accelerate"):
    importlib.import_module(m)
    print(m, "OK")
import torch
print("cuda", torch.cuda.is_available(), torch.cuda.get_device_capability(), torch.cuda.get_device_name(0))
PY
