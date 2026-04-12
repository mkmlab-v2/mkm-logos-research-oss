# -*- coding: utf-8 -*-
"""Sovereign vocab efficiency: shard keywords vs tokenizer (see spike_sovereign_vocab_efficiency.py)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sovereign_vocab_efficiency_stdout_schema_and_savings() -> None:
    script = ROOT / "scripts" / "spike_sovereign_vocab_efficiency.py"
    cp = subprocess.run(
        [
            sys.executable,
            str(script),
            "--samples",
            "40",
            "--seed",
            "7",
            "--stdout-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout.strip())
    assert doc.get("schema") == "spike_sovereign_vocab_efficiency_v1"
    assert doc.get("hypothesis_tier") == "B"
    assert doc.get("boundary_ack") is True
    for k in (
        "baseline_token_count",
        "sovereign_token_count",
        "delta_saving_ratio",
        "tokenizer",
        "phrases_mapped",
        "leaf_terms_sampled",
    ):
        assert k in doc
    base = int(doc["baseline_token_count"])
    sov = int(doc["sovereign_token_count"])
    assert base > 0 and sov > 0
    assert sov < base, (base, sov, doc)
    assert float(doc["delta_saving_ratio"]) > 0.0
