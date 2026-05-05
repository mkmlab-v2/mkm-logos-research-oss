from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_unified_symbolic_agct_meta_guard_v1.py"


def test_unified_meta_guard_hold_when_any_component_holds(tmp_path: Path) -> None:
    agct = tmp_path / "agct.json"
    agct.write_text(
        json.dumps(
            {
                "schema": "agct_sasang_size_overlay_runtime_stub_v1",
                "runtime_stub": {"enabled": False, "status": "HOLD_BY_GENERALIZATION_GUARD"},
                "holdout_runtime_guard_v1": {"guard_pass": False},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    symbolic = tmp_path / "symbolic.json"
    symbolic.write_text(
        json.dumps(
            {
                "schema": "symbolic_math_mapping_shadow_gate_v1",
                "decision": "PASS_SHADOW_STABLE",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "meta_guard.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--agct-runtime-stub-json",
            str(agct),
            "--symbolic-shadow-gate-json",
            str(symbolic),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "unified_symbolic_agct_meta_guard_v1"
    assert doc["decision"] == "HOLD_UNIFIED_META_GUARD"


def test_unified_meta_guard_pass_when_all_pass(tmp_path: Path) -> None:
    agct = tmp_path / "agct.json"
    agct.write_text(
        json.dumps(
            {
                "schema": "agct_sasang_size_overlay_runtime_stub_v1",
                "runtime_stub": {"enabled": True, "status": "READY_FOR_SHADOW_GUARD_PASS"},
                "holdout_runtime_guard_v1": {"guard_pass": True},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    symbolic = tmp_path / "symbolic.json"
    symbolic.write_text(
        json.dumps(
            {
                "schema": "symbolic_math_mapping_shadow_gate_v1",
                "decision": "PASS_SHADOW_STABLE",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "meta_guard.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--agct-runtime-stub-json",
            str(agct),
            "--symbolic-shadow-gate-json",
            str(symbolic),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["decision"] == "PASS_UNIFIED_META_GUARD"
