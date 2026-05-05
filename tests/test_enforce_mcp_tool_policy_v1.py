# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.5, M:0.7}
# Balance: 89
# Purpose: Regression tests for MCP policy allowlist and scoped deny patterns.
# Keywords: mcp, policy, allowlist, denylist, pytest

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "enforce_mcp_tool_policy_v1.py"


def test_policy_allows_safe_memory_search(tmp_path: Path) -> None:
    policy = ROOT / "docs/final/artifacts/mcp_tool_policy_v1.json"
    args_json = tmp_path / "args_ok.json"
    args_json.write_text(json.dumps({"query": "auth tradeoff notes"}, indent=2), encoding="utf-8")
    out_json = tmp_path / "out_ok.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--policy-json",
            str(policy),
            "--server",
            "project-0-workspace-athena-core",
            "--tool-name",
            "memory_search",
            "--args-json",
            str(args_json),
            "--out-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("pass") is True


def test_policy_blocks_scoped_dangerous_devops_command(tmp_path: Path) -> None:
    policy = ROOT / "docs/final/artifacts/mcp_tool_policy_v1.json"
    args_json = tmp_path / "args_bad.json"
    args_json.write_text(json.dumps({"command": "rm -rf /opt/app"}, indent=2), encoding="utf-8")
    out_json = tmp_path / "out_bad.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--policy-json",
            str(policy),
            "--server",
            "project-0-workspace-devops-mcp",
            "--tool-name",
            "execute_vps_command",
            "--args-json",
            str(args_json),
            "--out-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 1
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("pass") is False
    failures = doc.get("failures", [])
    assert any("scoped_deny_pattern_matched" in str(x) for x in failures)

