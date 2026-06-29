"""Smoke: Park1985 body paste ingest chain."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ingest_park1985_body_paste_smoke(tmp_path: Path) -> None:
    paste = tmp_path / "body.txt"
    paste.write_text(
        "闡幽抄 遺稿抄 濟衆新編 — (東武)格致藁 본문 각주 협약도서관 전사 smoke sample.\n"
        "朴奭彦 역주 1985 太陽社 199.1-이617ㄱ CNTS-00047835836 page capture placeholder.\n",
        encoding="utf-8",
    )
    anchor = tmp_path / "anchor.json"
    script = ROOT / "scripts" / "ingest_cheonyucho_park1985_body_paste_v1.py"
    bind = ROOT / "scripts" / "bind_cheonyucho_physical_anchor_v1.py"

    # Patch ingest to use tmp anchor via bind directly (ingest uses fixed DEFAULT_ANCHOR)
    proc = subprocess.run(
        [
            sys.executable,
            str(bind),
            "--paste-file",
            str(paste),
            "--slug",
            "PARK1985_NLK_BODY_pytest",
            "--call-no",
            "199.1-이617ㄱ",
            "--page",
            "pytest-smoke",
            "--anchor-out",
            str(anchor),
            "--no-patch-probe",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    proxy = ROOT / "docs/research/raw/CHEONYUCHO_PHYSICAL_PARK1985_NLK_BODY_pytest_nl_proxy.md"
    assert proxy.is_file()
    proxy.unlink(missing_ok=True)


def test_ingest_park1985_rejects_empty_drop_zone() -> None:
    script = ROOT / "scripts" / "ingest_cheonyucho_park1985_body_paste_v1.py"
    drop = ROOT / "data/corpus/ijeoma/originals/cheonyucho_partial/park1985_nlk_body_paste.md"
    proc = subprocess.run(
        [sys.executable, str(script), "--input", str(drop)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 1
    line = [ln for ln in proc.stdout.splitlines() if ln.strip().startswith("{")][-1]
    out = json.loads(line)
    assert out["ok"] is False
