"""Logos research text MVP — intake · report · handoff · spec chain."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_logos_jema_ai_research_handoff_v1 import build_handoff  # noqa: E402
from build_logos_research_text_mvp_spec_v1 import build_spec  # noqa: E402
from check_logos_research_text_mvp_intake_v1 import evaluate_intake  # noqa: E402
from core.logos_research_text_mvp_report_v1 import build_text_mvp_report  # noqa: E402


def test_intake_pass_sample_question():
    doc = evaluate_intake(
        question="욥기 고난과 의의 — 학파별 해석 차이는?",
        domain_lane="logos",
        intent_chip="reports",
    )
    assert doc["intake_gate"] == "PASS"
    assert not doc["failed_checks"]


def test_intake_hold_short_question():
    doc = evaluate_intake(question="알려줘", domain_lane="logos")
    assert doc["intake_gate"] == "HOLD"
    assert "question_too_short" in doc["failed_checks"]


def test_intake_pass_short_scripture_ref():
    doc = evaluate_intake(question="시편 23편", domain_lane="logos")
    assert doc["intake_gate"] == "PASS"
    assert not doc["failed_checks"]


def test_intake_hold_live_trading():
    doc = evaluate_intake(question="비트코인 지금 매수해도 되나 실매매로", domain_lane="logos")
    assert doc["intake_gate"] == "HOLD"
    assert "forbidden_live_trading" in doc["failed_checks"]


def test_build_text_mvp_report_sections():
    payload = {
        "research_only": True,
        "send_gate": "HOLD",
        "non_gating": True,
        "preset_id": "job_job_suffering_reason",
        "answer": "[HYPO] sample answer",
        "path": {
            "steps": ["lemma_faith", "Job.1.21"],
            "verse_refs": ["Job.1.21"],
            "node_ids": ["lemma_faith"],
        },
        "conflict_context": {
            "groups": [
                {
                    "conflict_group_id": "cg1",
                    "school_count": 1,
                    "schools": [
                        {
                            "school_tier": "historical",
                            "interpretation_ko": "test",
                            "citation_lock_anchors": ["Job.1.21"],
                        }
                    ],
                }
            ]
        },
    }
    report = build_text_mvp_report(payload, query="욥기 고난?", intake={"intake_gate": "PASS"})
    assert report["schema"] == "logos_research_text_mvp_report_v1"
    sections = report["sections"]
    assert sections["summary"]["body_ko"]
    assert "Job.1.21" in sections["citations"]["verse_refs"]
    assert sections["school_comparison"]["groups"]
    assert sections["word_network"]["path_steps"]
    assert sections["gematria_insight"]["rows"]
    assert report["governance"]["forbidden_claims"]


def test_build_logos_research_handoff_schema():
    doc = build_handoff(root=ROOT)
    assert doc["schema"] == "logos_jema_ai_research_handoff_v1"
    assert doc["surface"]["path"] == "/logos-research/ask"
    assert doc["surface"].get("inquiry_alias_path") == "/logos-research/inquiry"
    assert doc["surface"]["graphics_studio_excluded"] is True
    assert doc["api_contract"]["post_path"] == "/api/logos-research/query"
    assert doc["api_contract"].get("output_format") == "text_mvp_report_v1"
    assert doc["consumer_handoff"]["mkmlife_oracle_sphere_url"].startswith("https://")
    ns = doc.get("namespace_v1") or {}
    assert ns.get("domain_surface_hint") == "logos"
    assert ns.get("research_only") is True


def test_build_spec_artifact(tmp_path: Path):
    handoff_out = tmp_path / "handoff.json"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_jema_ai_research_handoff_v1.py"), "--out", str(handoff_out)],
        cwd=ROOT,
        check=True,
    )
    spec, sample = build_spec(root=ROOT)
    assert spec["schema"] == "logos_research_text_mvp_spec_v1"
    assert spec["page"]["path"] == "/logos-research/ask"
    assert spec["page"].get("inquiry_alias_path") == "/logos-research/inquiry"
    assert spec["api"]["path"] == "/api/logos-research/query"
    assert sample["schema"] == "logos_research_text_mvp_report_v1"
    assert set(sample["sections"].keys()) == {
        "summary",
        "citations",
        "school_comparison",
        "word_network",
        "gematria_insight",
    }


def test_inquiry_alias_page_exists():
    page = ROOT / "projects/no1kmedi/src/app/logos-research/inquiry/page.tsx"
    assert page.is_file()
    text = page.read_text(encoding="utf-8")
    assert 'redirect("/logos-research/ask")' in text


def test_chain_script_exit_zero():
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_research_text_mvp_chain_v1.py"),
            "--skip-pytest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    chain = json.loads((ROOT / "reports/logos_research_text_mvp_chain_v1_latest.json").read_text(encoding="utf-8"))
    assert chain["ok"] is True
    assert (ROOT / "docs/final/artifacts/logos_research_text_mvp_spec_v1_latest.json").is_file()
