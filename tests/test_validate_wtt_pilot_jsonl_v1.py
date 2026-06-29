"""WTT pilot JSONL validate — schema + PII scan."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/wtt/examples/wtt_spicy_masked_sessions_v1.example.jsonl"
VALIDATE = ROOT / "scripts/validate_wtt_pilot_jsonl_v1.py"
BUILD = ROOT / "scripts/build_wtt_spicy_masked_sessions_v1.py"


@pytest.fixture(scope="module")
def corpus_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("wtt") / "sessions.jsonl"
    subprocess.run(
        [sys.executable, str(BUILD), "--out-jsonl", str(out)],
        cwd=str(ROOT),
        check=True,
    )
    return out


def test_validate_spicy_corpus_ok(corpus_path: Path, tmp_path: Path) -> None:
    report_out = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(VALIDATE),
            "--jsonl",
            str(corpus_path),
            "--out",
            str(report_out),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(report_out.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["session_count"] >= 20


def test_validate_fails_on_unmasked_phone(tmp_path: Path, corpus_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    row = json.loads(corpus_path.read_text(encoding="utf-8").splitlines()[0])
    row["turns"][0]["text"] = "연락처 010-1234-5678 로 전화주세요"
    bad.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), "--jsonl", str(bad), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1


def test_committed_corpus_validates_if_present() -> None:
    if not CORPUS.is_file():
        pytest.skip("example corpus not built yet")
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), "--jsonl", str(CORPUS), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
