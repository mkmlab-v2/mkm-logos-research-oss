# Keywords: build_logos_b2b_verse_4d_appendix_v1

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/build_logos_b2b_verse_4d_appendix_v1.py"
FIXTURE = ROOT / "tests/data/logos_verse_4d_showroom_slice_fixture_v1.json"


def test_build_verse_4d_appendix_from_fixture_exit_zero() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "appendix.md"
        r = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--slice-json",
                str(FIXTURE),
                "--out-md",
                str(out),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr + r.stdout
        assert out.is_file()
        text = out.read_text(encoding="utf-8")
        assert "NON_GATING" in text
        assert "ready_for_external_send: false" in text
        assert "GEN.1.1" in text
        assert "null_vector_permutation" in text
        assert "cosmic OS" in text
        assert "Boundary (KO · EN)" in text


def test_build_verse_4d_appendix_missing_slice_graceful() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "appendix.md"
        missing = Path(tmp) / "no_slice.json"
        r = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--slice-json",
                str(missing),
                "--out-md",
                str(out),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr + r.stdout
        text = out.read_text(encoding="utf-8")
        assert "build_logos_verse_4d_showroom_slice_v1.py" in text
        assert "ready_for_external_send: false" in text
