"""Myeongri 표Ⅲ-1 Tier0 table extract."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_myeongri_yukchin_table_iii1_extract_v1() -> None:
    out = ROOT / "docs/final/artifacts/myeongri_yukchin_table_iii1_extract_v1_latest.json"
    cp = subprocess.run(
        ["py", str(ROOT / "scripts/build_myeongri_yukchin_table_iii1_extract_v1.py"), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "myeongri_yukchin_table_iii1_extract_v1"
    assert doc["table_ref"] == "표Ⅲ-1"
    assert doc["anchor_verified"] is True
    assert len(doc["rows"]) == 3
    corpora = {r["corpus"] for r in doc["rows"]}
    assert "연해자평(淵海子平)" in corpora
    assert "적천수(滴天髓)" in corpora
    assert "궁통보감(窮通寶鑑)" in corpora
