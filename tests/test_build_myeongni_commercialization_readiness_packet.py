from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "build_myeongni_commercialization_readiness_packet.py"


def test_runner_emits_readiness_packet_with_override_stats(tmp_path: Path) -> None:
    cp = subprocess.run(
        [sys.executable, str(_RUNNER)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert cp.returncode == 0, cp.stderr
    packet_path = _ROOT / "docs" / "final" / "artifacts" / "myeongni_commercialization_readiness_packet_latest.json"
    assert packet_path.is_file()
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet.get("schema") == "myeongni_commercialization_readiness_packet_v1"
    summary = packet.get("summary") or {}
    assert "shadow_override_ratio" in summary
    ratio = float(summary.get("shadow_override_ratio", 0.0))
    assert 0.0 <= ratio <= 1.0
    integrity = packet.get("shadow_history_integrity") or {}
    assert isinstance(integrity.get("history_rows"), int)
    assert isinstance(integrity.get("override_rows"), int)
    assert "shadow_override_ratio_limit" in summary
    assert "shadow_override_ratio_exceeded" in summary


def test_runner_downgrades_when_override_ratio_threshold_exceeded(tmp_path: Path) -> None:
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--max-shadow-override-ratio", "0.0"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert cp.returncode == 0, cp.stderr
    packet_path = _ROOT / "docs" / "final" / "artifacts" / "myeongni_commercialization_readiness_packet_latest.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    summary = packet.get("summary") or {}
    assert summary.get("shadow_override_ratio_exceeded") is True
    assert packet.get("readiness") in {"Almost", "Not yet"}
    warnings = packet.get("warnings") or []
    assert any("shadow_override_ratio_exceeded" in str(x) for x in warnings)
