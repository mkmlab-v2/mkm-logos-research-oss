# Keywords: compression enterprise readiness, lg deck

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_lg_compression_deck() -> None:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_lg_hs_compression_discipline_deck_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = ROOT / "docs/final/artifacts/lg_hs_compression_discipline_deck_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "lg_hs_compression_discipline_deck_v1"
    slides = doc.get("slides") or []
    assert len(slides) >= 9
    titles = [str(s.get("title") or "") for s in slides]
    assert any("Moat" in t for t in titles)
    assert any("Plug-in" in t for t in titles)
    forbidden = doc.get("forbidden_phrases") or []
    assert "17/17 passed" in forbidden
    assert "멀티 샤드 동시 활성화" in forbidden
    speaker = ROOT / "docs/final/artifacts/lg_hs_ir_moat_speaker_pack_v1_latest.md"
    assert speaker.is_file(), f"missing {speaker}"


def test_readiness_check_runs() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_compression_enterprise_summary_readiness_v1.py"),
            "--stdout-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    payload = json.loads(r.stdout.strip().splitlines()[-1])
    assert "ready_internal" in payload
