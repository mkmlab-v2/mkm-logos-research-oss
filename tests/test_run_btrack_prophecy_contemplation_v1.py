# @MKM12-METADATA
# Type: Logic
# Purpose: B-track prophecy contemplation pilot (pre-gate JSON + exit codes).
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "run_btrack_prophecy_contemplation_v1.py"
_GEN = _ROOT / "scripts" / "generate_btrack_hypothesis_prophecy_v1.py"


def test_contemplation_script_exists() -> None:
    assert _SCRIPT.is_file()


def test_contemplation_passes_minimal_bundle(tmp_path: Path) -> None:
    b = tmp_path / "bundle.json"
    b.write_text(json.dumps({"schema": "btrack_llm_input_bundle_v1", "artifacts": {}}, indent=2), encoding="utf-8")
    out = tmp_path / "contemplation.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--bundle",
            str(b),
            "--output",
            str(out),
            "--skip-audit-log",
            "--skip-gemini-reflect",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_prophecy_contemplation_v1"
    assert doc.get("review", {}).get("status") == "pass"


def test_contemplation_fails_on_btc_scope_violation(tmp_path: Path) -> None:
    b = tmp_path / "bad_bundle.json"
    b.write_text(
        json.dumps(
            {
                "schema": "btrack_llm_input_bundle_v1",
                "artifacts": {
                    "macro_independent_lens": {
                        "policy_scope": {"trading_primary_asset": "KOSPI200", "kospi_role": "gating"},
                    }
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "contemplation_bad.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--bundle",
            str(b),
            "--output",
            str(out),
            "--skip-audit-log",
            "--skip-gemini-reflect",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 1, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("review", {}).get("status") == "fail"


def test_generator_rejects_contemplation_bundle_sha_mismatch(tmp_path: Path) -> None:
    b = tmp_path / "bundle.json"
    b.write_text(json.dumps({"schema": "btrack_llm_input_bundle_v1", "artifacts": {}}, indent=2), encoding="utf-8")
    out_c = tmp_path / "contemplation.json"
    cp1 = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--bundle",
            str(b),
            "--output",
            str(out_c),
            "--skip-audit-log",
            "--skip-gemini-reflect",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp1.returncode == 0, cp1.stderr
    b.write_text(
        b.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    out_h = tmp_path / "hyp.json"
    cp2 = subprocess.run(
        [
            sys.executable,
            str(_GEN),
            "--bundle",
            str(b),
            "--stub",
            "--contemplation-json",
            str(out_c),
            "--output",
            str(out_h),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp2.returncode == 1, cp2.stdout + cp2.stderr
    assert "bundle_sha256 mismatch" in (cp2.stderr + cp2.stdout)


def test_generator_stub_includes_contemplation_provenance_when_aligned(tmp_path: Path) -> None:
    b = tmp_path / "bundle.json"
    b.write_text(json.dumps({"schema": "btrack_llm_input_bundle_v1", "artifacts": {}}, indent=2), encoding="utf-8")
    out_c = tmp_path / "contemplation.json"
    cp1 = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--bundle",
            str(b),
            "--output",
            str(out_c),
            "--skip-audit-log",
            "--skip-gemini-reflect",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp1.returncode == 0, cp1.stderr
    out_h = tmp_path / "hyp.json"
    cp2 = subprocess.run(
        [
            sys.executable,
            str(_GEN),
            "--bundle",
            str(b),
            "--stub",
            "--contemplation-json",
            str(out_c),
            "--output",
            str(out_h),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp2.returncode == 0, cp2.stderr + cp2.stdout
    hyp = json.loads(out_h.read_text(encoding="utf-8"))
    prov = hyp.get("provenance") if isinstance(hyp.get("provenance"), dict) else {}
    assert "btrack_prophecy_contemplation_v1" in prov
    assert prov["btrack_prophecy_contemplation_v1"].get("review_status") == "pass"


def test_contemplation_gemini_requested_without_api_key_fails(tmp_path: Path) -> None:
    b = tmp_path / "bundle.json"
    b.write_text(json.dumps({"schema": "btrack_llm_input_bundle_v1", "artifacts": {}}, indent=2), encoding="utf-8")
    out = tmp_path / "contemplation.json"
    env = os.environ.copy()
    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_STUDIO_API_KEY"):
        env.pop(k, None)
    env["MKM_BTRACK_CONTEMPLATION_USE_GEMINI"] = "1"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--bundle",
            str(b),
            "--output",
            str(out),
            "--skip-audit-log",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert cp.returncode == 1, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("review", {}).get("status") == "fail"
    assert doc.get("model_route") == "local_bundle_guard_v1+gemini_reflect_v1"
