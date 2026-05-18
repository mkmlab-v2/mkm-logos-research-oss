from __future__ import annotations

from pathlib import Path

from scripts.verify_p0_constitution_gate_paths_cloud_v1 import main, parse_required_paths


def test_parse_required_paths_non_empty() -> None:
    root = Path(__file__).resolve().parents[1]
    ps1 = root / "scripts" / "verify_p0_constitution_gate_paths.ps1"
    paths = parse_required_paths(ps1)
    assert len(paths) > 100
    assert "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md".replace(
        "/", "\\"
    ) in paths or any("CONSTITUTION_INFERENCE" in p for p in paths)


def test_cloud_gate_exit_zero_in_repo() -> None:
    assert main() == 0
