import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports/lexicon_hangul_curated_pilot_v1_latest.json"


def test_curated_pilot_both_pass_when_present():
    if not PILOT.is_file():
        return
    doc = json.loads(PILOT.read_text(encoding="utf-8"))
    assert doc.get("double_gate", {}).get("both_pass") is True
