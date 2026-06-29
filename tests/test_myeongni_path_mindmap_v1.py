"""Myeongni path mindmap contract smoke (TS is SSOT)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NO1K = ROOT / "projects" / "no1kmedi"
SCHEMA = ROOT / "docs" / "final" / "artifacts" / "myeongni_path_mindmap_schema_v1.json"


def test_schema_present() -> None:
    doc = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert doc["schema"] == "myeongni_path_mindmap_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["lens"] == "myeongni"


def test_ts_smoke_exit_0() -> None:
    proc = subprocess.run(
        ["npx", "--yes", "tsx", "scripts/smoke-myeongni-path-mindmap-v1.ts"],
        cwd=str(NO1K),
        capture_output=True,
        text=True,
        shell=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_myeongni_lite_enrich_shape() -> None:
    proc = subprocess.run(
        [
            "py",
            "scripts/saju_myeongni_lite_enrich_v1.py",
            "--birth-instant-utc",
            "1991-03-10T02:10:00Z",
            "--iana-tz",
            "Asia/Seoul",
            "--is-male",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        shell=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(proc.stdout)
    assert doc.get("schema") == "saju_myeongni_lite_enrich_v1"
    pillars = doc.get("pillars") or {}
    assert pillars.get("day"), pillars


def test_myeongni_full_report_cli_shape() -> None:
    proc = subprocess.run(
        [
            "py",
            "scripts/build_myeongni_full_report_v1.py",
            "--local",
            "1991",
            "3",
            "10",
            "11",
            "10",
            "0",
            "--iana-tz",
            "Asia/Seoul",
            "--is-male",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        shell=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(proc.stdout)
    assert doc.get("schema") == "myeongni_full_report_v1"
    pillars = doc.get("pillars") or {}
    assert pillars.get("day"), pillars


def test_myeongni_studio_smoke_chain_offline() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_myeongni_studio_smoke_chain_v1.py", "--skip-http"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        shell=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_render_myeongni_full_report_markdown_v1() -> None:
    build = subprocess.run(
        [
            "py",
            "scripts/build_myeongni_full_report_v1.py",
            "--local",
            "1991",
            "3",
            "10",
            "11",
            "10",
            "0",
            "--iana-tz",
            "Asia/Seoul",
            "--is-male",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        shell=True,
    )
    assert build.returncode == 0, build.stderr or build.stdout
    render = subprocess.run(
        ["py", "scripts/render_myeongni_full_report_markdown_v1.py"],
        cwd=str(ROOT),
        input=build.stdout,
        capture_output=True,
        text=True,
        shell=True,
    )
    assert render.returncode == 0, render.stderr or render.stdout
    assert "# MKM 명리 풀 리포트" in render.stdout
    assert "기묘" in render.stdout or "일주" in render.stdout


if __name__ == "__main__":
    test_schema_present()
    test_ts_smoke_exit_0()
    test_myeongni_lite_enrich_shape()
    test_myeongni_full_report_cli_shape()
    test_myeongni_studio_smoke_chain_offline()
    test_render_myeongni_full_report_markdown_v1()
    print("ok")
