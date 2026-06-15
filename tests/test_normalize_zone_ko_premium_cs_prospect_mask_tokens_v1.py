"""Mask normalization for KO CS prospects skipped with missing_mask_token."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/normalize_zone_ko_premium_cs_prospect_mask_tokens_v1.py"
PROSPECT = ROOT / "codebook/templates/zone_ko_premium_cs_templates_prospect_v1.jsonl"


def test_normalize_mask_tokens_adds_block_mask(tmp_path: Path) -> None:
    prospect = tmp_path / "prospect.jsonl"
    prospect.write_text(
        json.dumps(
            {
                "template_id": "kcs_p006",
                "shard_id": "zone_ko_premium_cs_v1",
                "language": "ko",
                "snippet": "오늘 상담 건 정리 부탁합니다. 이*민 고객 케이스요.",
                "must_keep_terms": ["고객", "상담"],
                "prospect": True,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--prospect", str(prospect)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    row = json.loads(prospect.read_text(encoding="utf-8").strip())
    assert "███" in row["snippet"]
    assert "███" in row["must_keep_terms"]


def test_production_prospects_include_mask_for_p006() -> None:
    if not PROSPECT.is_file():
        import pytest

        pytest.skip("prospect catalog missing")
    rows = [json.loads(line) for line in PROSPECT.read_text(encoding="utf-8").splitlines() if line.strip()]
    p006 = next(r for r in rows if r.get("template_id") == "kcs_p006")
    assert "███" in p006["snippet"]
