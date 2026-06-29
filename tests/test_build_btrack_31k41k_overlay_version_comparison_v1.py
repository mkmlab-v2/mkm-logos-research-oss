"""Smoke test for overlay version comparison builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_btrack_31k41k_overlay_version_comparison_v1.py"
OUT = ROOT / "reports/btrack_31k41k_overlay_version_comparison_v1_latest.json"


def test_overlay_version_comparison_builds() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_31k41k_overlay_version_comparison_v1"
    v2 = next(v for v in doc["versions"] if v["overlay_version"] == "v2")
    assert v2["fold"]["path"].endswith("btrack_31k41k_prophecy_shadow_fold_stability_v2_v1_latest.json")
    assert doc.get("routing_ab", {}).get("path")


def test_fold_stability_resolve_out_json() -> None:
    import importlib.util

    mod_path = ROOT / "scripts" / "run_btrack_31k41k_prophecy_shadow_fold_stability_v1.py"
    spec = importlib.util.spec_from_file_location("fold_stab", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    assert mod.resolve_default_fold_out("v2", mod.DEFAULT_OUT) == mod.DEFAULT_OUT_V2
    assert mod.resolve_default_fold_out("v2c", mod.DEFAULT_OUT) == mod.DEFAULT_OUT_V2C
    assert mod.resolve_default_fold_out("v2b", mod.DEFAULT_OUT) == mod.DEFAULT_OUT_V2B_MAX
