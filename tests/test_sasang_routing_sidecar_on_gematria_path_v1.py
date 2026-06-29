"""B-track lab: sasang routing sidecar on gematria path (no score fusion)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "docs/final/artifacts/sasang_routing_sidecar_on_gematria_path_v1_latest.json"
CHAIN = ROOT / "reports/sasang_routing_sidecar_on_gematria_path_chain_v1_latest.json"


def test_build_sidecar_exit0() -> None:
    cp = subprocess.run(
        [sys.executable, "scripts/build_sasang_routing_sidecar_on_gematria_path_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    assert SIDECAR.is_file()
    doc = json.loads(SIDECAR.read_text(encoding="utf-8"))
    assert doc["schema"] == "sasang_routing_sidecar_on_gematria_path_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["forbidden_synthesis_ack"] is True
    assert "prophecy_vote" in doc["must_not_merge_into"]


def test_gate_passes_on_built_sidecar() -> None:
    cp = subprocess.run(
        [sys.executable, "scripts/check_sasang_routing_sidecar_on_gematria_path_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout


def test_gate_fails_on_forbidden_merge_key(tmp_path: Path) -> None:
    doc = json.loads(SIDECAR.read_text(encoding="utf-8"))
    doc["merged_score"] = 0.99
    bad = tmp_path / "bad_sidecar.json"
    bad.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    cp = subprocess.run(
        [
            sys.executable,
            "scripts/check_sasang_routing_sidecar_on_gematria_path_v1.py",
            "--in",
            str(bad),
            "--out",
            str(tmp_path / "gate.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 1


def test_chain_exit0() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            "scripts/run_sasang_routing_sidecar_on_gematria_path_chain_v1.py",
            "--skip-separation",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    assert CHAIN.is_file()
    chain = json.loads(CHAIN.read_text(encoding="utf-8"))
    assert chain["all_ok"] is True
