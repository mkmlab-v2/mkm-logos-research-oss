# Purpose: v4 posteval bundle smoke on fixture-sized eval.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_build_v4_posteval_bundle_imports() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", "from scripts.build_myeongri_interpret_v4_posteval_bundle_v1 import main"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
