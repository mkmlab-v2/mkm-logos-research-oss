#!/usr/bin/env python3
"""Aggregate NVIDIA GPU credit lane status (NIM + Innovation Lab + local). No secrets."""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/final/artifacts/nvidia_gpu_credit_lane_policy_v1.json"
POINTER = ROOT / "reports/nvidia_inception_account_pointer_v1.json"
OUT = ROOT / "reports/nvidia_gpu_credit_ops_status_v1_latest.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else {}


def _nim_probe() -> dict:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    except ImportError:
        pass
    key = os.getenv("NVIDIA_API_KEY") or os.getenv("NGC_API_KEY")
    if not key:
        return {"ok": False, "error": "no_api_key"}
    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.loads(r.read().decode("utf-8"))
        n = len(data.get("data") or [])
        return {"ok": True, "http_status": r.status, "model_count": n}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main() -> int:
    policy = _load(POLICY)
    pointer = _load(POINTER)
    lab = (pointer.get("innovation_lab_brev") or {}) if pointer else {}
    doc = {
        "schema": "nvidia_gpu_credit_ops_status_v1",
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "b_track_infra",
        "kaggle_gpu": "cancelled_per_commander",
        "inference_nim": _nim_probe(),
        "innovation_lab_brev": {
            "status": lab.get("status", "unknown"),
            "outcome": lab.get("outcome"),
            "review_sla_weeks": lab.get("review_sla_weeks"),
            "gpu_available_now": lab.get("status") == "accepted",
        },
        "local_rtx_5060_ti": {
            "role": "embed + 8B ollama only",
            "train_30b_qlora": "blocked",
        },
        "recommended_commands": {
            "api_primary": "powershell -File scripts/Run-NvidiaApiPrimary_v1.ps1",
            "nim_chat": "py scripts/nvidia_nim_chat_v1.py chat --model meta/llama-3.3-70b-instruct --prompt \"...\"",
            "full_stack": "powershell -File scripts/Run-NvidiaCreditGpuLane_v1.ps1",
            "phase2": "powershell -File scripts/Run-NvidiaCreditGpuLanePhase2_v1.ps1",
            "phase3": "powershell -File scripts/Run-NvidiaCreditGpuLanePhase3_v1.ps1",
            "await_lab": "Monitor @nvidia.com for Innovation Lab accept/reject",
        },
        "nim_registry": "docs/final/artifacts/nvidia_nim_model_registry_v1.json",
        "policy_path": str(POLICY.relative_to(ROOT)).replace("\\", "/"),
        "pointer_path": str(POINTER.relative_to(ROOT)).replace("\\", "/"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0 if doc["inference_nim"].get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
