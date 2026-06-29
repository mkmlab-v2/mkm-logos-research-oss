"""Offline: Magic Orb design readiness SSOT structure + builder merge."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_magic_orb_design_readiness_v1.py"
PLAYWRIGHT = ROOT / "projects/mkm/mkm-life/scripts/capture-magic-orb-design-readiness-playwright.mjs"
CHAIN = ROOT / "scripts/run_magic_orb_design_readiness_chain_v1.py"


def test_playwright_script_has_design_checks():
    text = PLAYWRIGHT.read_text(encoding="utf-8")
    assert "no_artifact_strip_hypo_tag" in text
    assert "no_generator_script_path_visible" in text
    assert "magic_orb_design_screenshot_latest.png" in text
    assert "report_phase_reachable" in text
    assert "consumer_report_summary_present" in text


def test_builder_consumer_ready_requires_commander_pass():
    out_path = ROOT / "reports/magic_orb_design_readiness_v1_test_isolated.json"
    subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--commander-visual-ok",
            "false",
            "--out",
            str(out_path),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads(out_path.read_text(encoding="utf-8-sig"))
    assert out["schema"] == "magic_orb_design_readiness_v1"
    assert out["consumer_ready"] is False
    assert "messaging_contract" in out
    assert "probe all_ok" in out["messaging_contract"]["disallowed_when_consumer_ready_false"][2]


def test_builder_design_fail_when_playwright_hypo_checks_fail(tmp_path: Path):
    pw_path = tmp_path / "playwright.json"
    eng_path = tmp_path / "engineering.json"
    out_path = tmp_path / "readiness.json"
    pw_path.write_text(
        json.dumps(
            {
                "schema": "magic_orb_design_readiness_playwright_v1",
                "design_ok": False,
                "checks": [{"id": "no_artifact_strip_hypo_tag", "ok": False, "consumer_blocker": True}],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    eng_path.write_text(
        json.dumps({"all_ok": True, "profile": "core"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--commander-visual-ok",
            "true",
            "--playwright-json",
            str(pw_path),
            "--engineering-probe",
            str(eng_path),
            "--out",
            str(out_path),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads(out_path.read_text(encoding="utf-8-sig"))
    assert out["engineering_ok"] is True
    assert out["design_ok"] is False
    assert out["consumer_ready"] is False
    assert "design FAIL" in out["verdict_ko"]


def test_chain_wrapper_exists():
    assert "capture-magic-orb-design-readiness-playwright.mjs" in CHAIN.read_text(encoding="utf-8")
