import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "reports/hangul_curated_track_a_promotion_packet_v1_latest.json"


def test_promotion_packet_scope_excludes_active_write():
    if not PACKET.is_file():
        return
    doc = json.loads(PACKET.read_text(encoding="utf-8"))
    scope = doc.get("promotion_scope") or {}
    assert scope.get("multilens_active_report_write") is False
    assert scope.get("lexicon_production_ssot_swap") is True
