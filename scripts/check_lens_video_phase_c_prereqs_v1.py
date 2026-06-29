#!/usr/bin/env python3
"""Prereq probe for lens video Phase C (AnimateDiff / LTX hypo vs PIL+ffmpeg baseline)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _probe_torch_cuda() -> tuple[bool, str | None]:
    try:
        import torch  # noqa: WPS433

        return bool(torch.cuda.is_available()), getattr(torch.version, "cuda", None)
    except Exception:
        return False, None


def _probe_diffusers() -> bool:
    try:
        import diffusers  # noqa: F401, WPS433

        return True
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=ROOT / "reports/lens_video_phase_c_prereqs_v1_latest.json")
    args = ap.parse_args()

    cuda_ok, cuda_ver = _probe_torch_cuda()
    report: dict[str, object] = {
        "schema": "lens_video_phase_c_prereqs_v1",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now_z(),
        "checks": {
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "pil": False,
            "torch_cuda": cuda_ok,
            "diffusers": _probe_diffusers(),
        },
        "engines": {
            "pil_animated_v2": {"status": "available", "note": "scripts/build_lens_btrack_video_loops_v1.py"},
            "animatediff_hypo": {
                "status": "wired_hypo",
                "note": "scripts/video/animatediff_hypo_external_generator_v1.py",
            },
            "ltx_hypo": {"status": "research_only", "note": "not wired; HF model bake TBD"},
        },
        "cuda_version": cuda_ver,
        "ok": False,
    }
    try:
        import PIL  # noqa: F401, WPS433

        report["checks"]["pil"] = True  # type: ignore[index]
    except Exception:
        pass

    checks = report["checks"]
    assert isinstance(checks, dict)
    baseline_ok = bool(checks.get("ffmpeg")) and bool(checks.get("pil"))
    report["ok"] = baseline_ok
    report["baseline_ready"] = baseline_ok
    report["gpu_hypo_ready"] = bool(checks.get("torch_cuda")) and bool(checks.get("diffusers"))

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if baseline_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
