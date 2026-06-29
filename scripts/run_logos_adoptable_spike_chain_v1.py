#!/usr/bin/env python3
"""Adoptable 3-pack spike chain — morphology · gematria matrix · cross-ref sample.

B-track only · tier_0 · completion JSON.

Reproducible:
  py scripts/run_logos_adoptable_spike_chain_v1.py
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
PY = sys.executable
OUT_COMPLETION = ROOT / "reports/logos_adoptable_spike_chain_v1_latest.json"
OUT_ARTIFACT = ROOT / "docs/final/artifacts/logos_adoptable_spike_chain_v1_latest.json"

STEPS = [
    ("morphology_frequency", [PY, "scripts/build_logos_morphology_frequency_report_v1.py"]),
    ("gematria_matrix", [PY, "scripts/export_logos_gematria_matrix_snapshot_v1.py"]),
    ("cross_ref_sample", [PY, "scripts/export_logos_cross_ref_sample_shard_v1.py"]),
    ("preset_taxonomy", [PY, "scripts/build_logos_studio_preset_taxonomy_v1.py"]),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "step": name,
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "").strip()[-400:],
        "stderr_tail": (proc.stderr or "").strip()[-400:],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-studio-copy", action="store_true", help="cross-ref step skips studio copy")
    args = ap.parse_args()

    nodes: list[dict[str, Any]] = []
    ok_all = True
    for name, cmd in STEPS:
        run_cmd = list(cmd)
        if name == "cross_ref_sample" and args.skip_studio_copy:
            run_cmd.append("--skip-studio")
        node = _run_step(name, run_cmd)
        nodes.append(node)
        if not node["ok"]:
            ok_all = False

    artifact_paths = {
        "morphology_frequency": "docs/final/artifacts/logos_morphology_frequency_report_v1_latest.json",
        "gematria_matrix": "docs/final/artifacts/logos_gematria_matrix_snapshot_v1_latest.json",
        "cross_ref_sample": "docs/final/artifacts/logos_cross_ref_sample_shard_v1_latest.json",
        "preset_taxonomy": "docs/final/artifacts/logos_studio_preset_taxonomy_v1_latest.json",
    }

    completion = {
        "schema": "logos_adoptable_spike_chain_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "quality_ok": ok_all,
        "exit_code": 0 if ok_all else 1,
        "reproducible_command": "py scripts/run_logos_adoptable_spike_chain_v1.py",
        "nodes": nodes,
        "artifact_paths": artifact_paths,
        "honesty_ack": {
            "tsk_63779_immediate_load": False,
            "marketing_4d_realtime_os": False,
            "curated_preset_studio": True,
        },
    }

    OUT_COMPLETION.parent.mkdir(parents=True, exist_ok=True)
    OUT_COMPLETION.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    OUT_ARTIFACT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok_all, "report": str(OUT_COMPLETION)}, ensure_ascii=False))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
