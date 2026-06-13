"""Tier 3 Cursor wire handoff pilot smoke."""



from __future__ import annotations



import json

from pathlib import Path



from scripts.build_a2a_tier3_cursor_wire_handoff_pilot_v1 import (

    JACCARD_ADAPT_FLOOR,

    build_tier3_document,

    lane_artifact_paths,

    render_brief_md,

)





def test_tier3_document_ok_oracle():

    doc = build_tier3_document(Path(__file__).resolve().parents[1], lane="oracle")

    assert doc["schema"] == "a2a_tier3_cursor_wire_handoff_pilot_v1"

    assert doc["tier"] == "tier3_cursor_parallel_chat"

    assert doc["pilot_ok"] is True

    kpi = doc["kpi_headline"]

    assert kpi["inject_tokens"] >= 32

    assert kpi["decision"] == "compressed"

    assert kpi["expand_jaccard"] is not None

    assert kpi["expand_jaccard"] >= JACCARD_ADAPT_FLOOR

    assert doc["lane_artifacts"]["brief"].endswith("a2a_tier3_cursor_wire_handoff_brief_oracle_v1_latest.md")





def test_web_ops_adaptive_meets_jaccard_floor():
    doc = build_tier3_document(Path(__file__).resolve().parents[1], lane="web_ops")
    kpi = doc["kpi_headline"]
    opts = doc["options"]
    floor = opts.get("jaccard_adapt_floor", JACCARD_ADAPT_FLOOR)
    assert doc["pilot_ok"] is True
    assert kpi["expand_jaccard"] is not None
    assert kpi["expand_jaccard"] >= floor
    assert opts.get("loss_profile_used") == "lossless_text"





def test_brief_md_contains_lane_and_hold():

    doc = build_tier3_document(Path(__file__).resolve().parents[1], lane="ms")

    md = render_brief_md(doc)

    assert "SEND_GATE: HOLD" in md

    assert "`ms`" in md

    assert "a2a_tier3_cursor_wire_handoff_brief_ms_v1_latest.md" in md

    assert "mkm_chat_resume_pack_latest.md" in md





def test_cli_writes_lane_artifacts(tmp_path, monkeypatch):

    root = Path(__file__).resolve().parents[1]

    paths = lane_artifact_paths(root, "infra")

    out = tmp_path / "pilot.json"

    brief = tmp_path / "brief.md"

    packet = tmp_path / "packet.json"

    log = tmp_path / "log.jsonl"

    monkeypatch.setattr(

        "sys.argv",

        [

            "build_a2a_tier3_cursor_wire_handoff_pilot_v1.py",

            "--lane",

            "infra",

            "--out",

            str(out),

            "--brief-out",

            str(brief),

            "--packet-out",

            str(packet),

            "--log",

            str(log),

            "--append-log",

            "--skip-lane-index",

        ],

    )

    from scripts.build_a2a_tier3_cursor_wire_handoff_pilot_v1 import main



    assert main() == 0

    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload.get("pilot_ok") is True

    assert payload["lane_artifacts"]["pilot"] == paths["pilot"].relative_to(root).as_posix()

    assert brief.read_text(encoding="utf-8").startswith("# Tier 3")

    assert packet.read_text(encoding="utf-8").startswith("{")

    assert len(log.read_text(encoding="utf-8").strip().splitlines()) == 1


