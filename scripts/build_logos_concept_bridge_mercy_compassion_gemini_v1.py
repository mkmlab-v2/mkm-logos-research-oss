#!/usr/bin/env python3
"""Bridge #6: mercy after turmoil via Gemini ([HYPO], aligns q03 gold)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_concept_bridge_mercy_compassion_gemini_v1_latest.json"
CONCEPT_KO = "혼란과 상실 이후의 긍휴와 자비"
CONCEPT_ID = "concept:mercy_after_turmoil"


def main() -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_logos_concept_bridge_gemini_v1.py"),
        "--concept-ko",
        CONCEPT_KO,
        "--concept-id",
        CONCEPT_ID,
        "--output-json",
        str(DEFAULT_OUT),
        "--raw-out",
        str(ROOT / "reports/gemini_batch/logos_concept_bridge_mercy_compassion_gemini_v1_raw.txt"),
    ]
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
