from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "check_truthfulqa_ab_gate_v1.py"


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_truthfulqa_gate_go(tmp_path: Path) -> None:
    mc = tmp_path / "mc.json"
    gen = tmp_path / "gen.json"
    out = tmp_path / "gate.json"
    _write_json(mc, {"comparative": {"accuracy_delta": 0.01, "hallucination_rate_proxy_delta": -0.02}})
    _write_json(gen, {"comparative": {"accuracy_delta": 0.005, "hallucination_rate_proxy_delta": -0.01}})

    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--mc-json",
            str(mc),
            "--generation-json",
            str(gen),
            "--out-json",
            str(out),
            "--strict",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["decision"] == "GO"
    assert doc["strict"]["summary"]["decision"] == "GO"
    assert "research_relaxed" in doc
    assert doc["research_relaxed"]["summary"]["decision"] == "GO"


def test_truthfulqa_gate_no_go_strict(tmp_path: Path) -> None:
    mc = tmp_path / "mc.json"
    gen = tmp_path / "gen.json"
    out = tmp_path / "gate.json"
    _write_json(mc, {"comparative": {"accuracy_delta": -0.1, "hallucination_rate_proxy_delta": 0.2}})
    _write_json(gen, {"comparative": {"accuracy_delta": -0.02, "hallucination_rate_proxy_delta": 0.05}})

    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--mc-json",
            str(mc),
            "--generation-json",
            str(gen),
            "--out-json",
            str(out),
            "--strict",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 1
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["decision"] == "NO_GO"
    assert doc["strict"]["summary"]["decision"] == "NO_GO"


def test_truthfulqa_gate_strict_no_go_relaxed_go(tmp_path: Path) -> None:
    """Strict fails generation hallucination; relaxed tier passes with higher ceiling."""
    mc = tmp_path / "mc.json"
    gen = tmp_path / "gen.json"
    out = tmp_path / "gate.json"
    _write_json(
        mc,
        {"comparative": {"accuracy_delta": 0.44, "hallucination_rate_proxy_delta": -0.44}},
    )
    _write_json(
        gen,
        {"comparative": {"accuracy_delta": 0.05, "hallucination_rate_proxy_delta": 0.02}},
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--mc-json",
            str(mc),
            "--generation-json",
            str(gen),
            "--out-json",
            str(out),
            "--relaxed-max-generation-hallucination-delta",
            "0.025",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["strict"]["summary"]["decision"] == "NO_GO"
    assert doc["research_relaxed"]["summary"]["decision"] == "GO"


def test_truthfulqa_gate_mc_only_go_without_generation_file(tmp_path: Path) -> None:
    """MC-only: no generation JSON; strict passes on MC deltas only."""
    mc = tmp_path / "mc.json"
    out = tmp_path / "gate.json"
    missing_gen = tmp_path / "nope.json"
    _write_json(mc, {"comparative": {"accuracy_delta": 0.01, "hallucination_rate_proxy_delta": -0.02}})

    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--mc-json",
            str(mc),
            "--generation-json",
            str(missing_gen),
            "--out-json",
            str(out),
            "--mc-only",
            "--strict",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("evaluation_mode") == "mc_only"
    assert doc["summary"]["decision"] == "GO"
    assert doc["strict"]["summary"]["total"] == 2
    assert "research_relaxed" not in doc


def test_truthfulqa_gate_mc_only_no_go_strict(tmp_path: Path) -> None:
    mc = tmp_path / "mc.json"
    out = tmp_path / "gate.json"
    gen = tmp_path / "gen.json"
    _write_json(mc, {"comparative": {"accuracy_delta": -0.1, "hallucination_rate_proxy_delta": 0.2}})
    _write_json(gen, {"comparative": {"accuracy_delta": 0.5, "hallucination_rate_proxy_delta": -0.1}})

    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--mc-json",
            str(mc),
            "--generation-json",
            str(gen),
            "--out-json",
            str(out),
            "--mc-only",
            "--strict",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 1
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["decision"] == "NO_GO"
    assert doc["strict"]["summary"]["decision"] == "NO_GO"
    # generation file present but ignored for checks
    assert doc["strict"]["summary"]["total"] == 2


def test_truthfulqa_gate_no_research_relaxed(tmp_path: Path) -> None:
    mc = tmp_path / "mc.json"
    gen = tmp_path / "gen.json"
    out = tmp_path / "gate.json"
    _write_json(mc, {"comparative": {"accuracy_delta": 0.01, "hallucination_rate_proxy_delta": -0.02}})
    _write_json(gen, {"comparative": {"accuracy_delta": 0.005, "hallucination_rate_proxy_delta": -0.01}})

    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--mc-json",
            str(mc),
            "--generation-json",
            str(gen),
            "--out-json",
            str(out),
            "--no-research-relaxed",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "research_relaxed" not in doc

