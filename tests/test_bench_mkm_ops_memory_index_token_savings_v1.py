"""Token bench smoke for ops memory index ([HYPO])."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bench_mkm_ops_memory_index_token_savings_v1 import (  # noqa: E402
    _count_tokens,
    _inject_repair_v2_text,
)

SCRIPT = ROOT / "scripts" / "bench_mkm_ops_memory_index_token_savings_v1.py"


def test_count_tokens_returns_method_and_positive_count() -> None:
    result = _count_tokens("abcd")
    assert result["tokens"] >= 1
    assert "method" in result


def test_inject_repair_v2_text_returns_guarded_payload() -> None:
    if not (ROOT / "MISSION_LOG.md").is_file():
        pytest.skip("MISSION_LOG.md required for ops memory index bench")
    if not (ROOT / "storage/meta/mkm_ops_memory_index_v1.json").is_file():
        pytest.skip("ops memory index missing")
    text, query = _inject_repair_v2_text(ROOT, top_n=2, slice_max_chars=400)
    assert isinstance(query, str)
    assert isinstance(text, str)


def test_token_savings_bench_cli_smoke(tmp_path: Path) -> None:
    if not (ROOT / "MISSION_LOG.md").is_file():
        pytest.skip("MISSION_LOG.md required")
    out = tmp_path / "token_bench.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--workspace-root",
            str(ROOT),
            "--out",
            str(out),
            "--top-n",
            "2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_ops_memory_index_token_bench_v1"
    assert "raw" in doc
    assert "repair_v2" in doc
    assert "delta" in doc
    assert doc["repair_v2"]["operational_label"] == "post-processor included"
    assert doc["delta"]["tokens_repair_v2_minus_raw"] is not None
