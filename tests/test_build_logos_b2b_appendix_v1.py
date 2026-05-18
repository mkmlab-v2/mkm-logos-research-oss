# Keywords: build_logos_b2b_appendix_v1

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/build_logos_b2b_appendix_v1.py"
OUT = ROOT / "docs/final/artifacts/track_c_b2b_logos_lens_appendix_v1_latest.md"


def test_build_appendix_exit_zero() -> None:
    r = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert OUT.is_file()
    text = OUT.read_text(encoding="utf-8")
    assert "NON_GATING" in text
    assert "DRAFT_AUTO" in text
    assert "theme_01" in text or "피와 물" in text
    assert "jemaai.cloud/public_showroom_logos_research" in text
