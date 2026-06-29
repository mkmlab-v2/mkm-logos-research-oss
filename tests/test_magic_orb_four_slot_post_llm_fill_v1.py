# Keywords: magic_orb, post_llm_fill, four_slot, template_expand

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
ENVELOPE = ROOT / "docs/final/artifacts/logos_four_slot_generation_envelope_v1_latest.json"
INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"


def _minimal_insight() -> dict:
    base = json.loads(INSIGHT.read_text(encoding="utf-8"))
    four = base.get("four_slot_response_v1") or {}
    slots = four.get("slots") or {}
    slim = {
        "four_slot_response_v1": {
            "schema_version": "four_slot_response_v1",
            "slot_order": four.get("slot_order") or [
                "fact_locked",
                "corpus_bound",
                "imagination_path",
                "unknown_gap",
            ],
            "slots": {
                "fact_locked": {"items": [], "empty_reason": "verified_anchor=false"},
                "corpus_bound": slots.get("corpus_bound") or {"items": []},
                "imagination_path": {
                    "items": [
                        {
                            "item_id": "school.test",
                            "text_ko": "시드 미리보기 텍스트.",
                            "label_ko": "테스트 학파",
                            "school_id": "test_school",
                            "must_not_present_as_fact": True,
                        }
                    ]
                },
                "unknown_gap": {
                    "items": [
                        {
                            "item_id": "gap.test",
                            "text_ko": "본문 밖 단정 불가.",
                            "must_not_present_as_fact": True,
                        }
                    ]
                },
            },
        }
    }
    return slim


def test_template_expand_quality() -> None:
    from magic_orb_four_slot_post_llm_fill_v1 import apply_post_llm_fill, quality_check

    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    insight = _minimal_insight()
    updated, report = apply_post_llm_fill(
        insight,
        envelope=envelope,
        mode="template_expand",
        human_gate_ack=True,
    )
    assert report["ok"] is True
    assert report["items_total"] >= 2
    meta = updated["four_slot_response_v1"]["post_llm_fill_v1"]
    assert meta["send_gate"] == "HOLD"
    assert meta["mode"] == "template_expand"
    errors = quality_check(updated, envelope)
    assert errors == [], errors
    text = updated["four_slot_response_v1"]["slots"]["imagination_path"]["items"][0]["text_ko"]
    assert text.startswith("[HYPO")
    assert "Fact-Lock 100%" not in text


def _last_json_line(stdout: str) -> dict:
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise AssertionError(f"no json in stdout: {stdout[:400]}")


def test_fill_chain_cli_template_expand() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_magic_orb_four_slot_post_llm_fill_chain_v1.py"),
            "--human-gate-ack",
            "--mode",
            "template_expand",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = _last_json_line(r.stdout)
    assert out["ok"] is True
    assert out["send_gate"] == "HOLD"
    chain = ROOT / "reports/magic_orb_four_slot_post_llm_fill_chain_v1_latest.json"
    assert chain.is_file()
    boundary = ROOT / "docs/final/artifacts/magic_orb_four_slot_product_boundary_v1_latest.json"
    assert boundary.is_file()
