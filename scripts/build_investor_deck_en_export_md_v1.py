#!/usr/bin/env python3
"""Build EN investor deck Markdown export from CSV (internal · print/PDF paste)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_investor_deck_ko_export_md_v1.py"


def main() -> int:
    csv_path = ROOT / "docs/research/MKM_UNIVERSAL_ROOT_INVESTOR_DECK_SLIDES_EN_V1.csv"
    out_path = ROOT / "docs/research/MKM_UNIVERSAL_ROOT_INVESTOR_DECK_EXPORT_EN_V1.md"
    report_path = ROOT / "reports/investor_deck_en_export_v1_latest.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--csv",
            str(csv_path),
            "--out",
            str(out_path),
            "--report",
            str(report_path),
        ],
        cwd=str(ROOT),
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    text = out_path.read_text(encoding="utf-8")
    text = text.replace("Investor Deck Export (KO v1.1)", "Investor Deck Export (EN v1.1)", 1)
    out_path.write_text(text, encoding="utf-8")
    print(f'{{"ok": true, "out": "{out_path.as_posix()}"}}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
