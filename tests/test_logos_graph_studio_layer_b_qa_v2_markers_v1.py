from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts/check_logos_graph_studio_layer_b_qa_v2_markers_v1.py"
CONTRACT = ROOT / "docs/final/artifacts/logos_graph_studio_layer_b_ux_contract_v1.json"
KERNEL = ROOT / "docs/final/artifacts/sasang_design_primitive_kernel_v1_latest.json"


def test_layer_b_check_script_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_layer_b_contract_embed_example():
    doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert "embed=hero" in doc.get("embed_example", "")
    assert doc.get("product_depth_host") == "logos.jema-ai.com"


def test_kernel_logos_product_depth():
    doc = json.loads(KERNEL.read_text(encoding="utf-8"))
    logos = doc["product_depth"]["logos.jema-ai.com"]
    assert logos["extensions"] == ["logos"]
    assert "survival" in logos["primitives"]
