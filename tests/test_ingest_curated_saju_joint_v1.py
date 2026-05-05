"""Offline tests for ingest_curated_saju_joint_v1 (provenance gate + promotion shape)."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import unittest.mock as mock
from contextlib import nullcontext, redirect_stdout
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "scripts" / "ingest_curated_saju_joint_v1.py"


def _load_ingest_module() -> Any:
    spec = importlib.util.spec_from_file_location("ingest_curated_saju_joint_v1", INGEST)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load ingest module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_ingest_main(
    tmp_input: Path,
    tmp_target: Path,
    *,
    dry_run: bool = False,
    fake_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> tuple[int, dict]:
    mod = _load_ingest_module()
    argv = [
        "ingest_curated_saju_joint_v1",
        "--input-jsonl",
        str(tmp_input),
        "--target-jsonl",
        str(tmp_target),
    ]
    if dry_run:
        argv.append("--dry-run")
    buf = io.StringIO()
    ctx = mock.patch.object(mod.subprocess, "run", side_effect=fake_run) if fake_run else nullcontext()
    with ctx, mock.patch.object(sys, "argv", argv), redirect_stdout(buf):
        code = mod.main()
    raw = buf.getvalue().strip()
    summary: dict[str, Any]
    try:
        summary = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        summary = {"parse_error": raw}
    return code, summary


def test_skip_unverified_without_url_or_citation(tmp_path: Path) -> None:
    inp = tmp_path / "in.jsonl"
    inp.write_text(
        json.dumps(
            {
                "name": "Nobody",
                "dob_utc": "2000-01-01T12:00:00Z",
                "is_male": True,
                "iana_tz": "Etc/UTC",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    tgt = tmp_path / "out.jsonl"
    code, summary = _run_ingest_main(inp, tgt)
    assert code == 0
    assert summary.get("skip_unverified") == 1
    assert summary.get("appended") == 0
    actions = summary.get("actions") or []
    assert any(a.get("action") == "SKIP_UNVERIFIED" for a in actions)


def test_append_when_provenance_ok(tmp_path: Path) -> None:
    inp = tmp_path / "in.jsonl"
    inp.write_text(
        json.dumps(
            {
                "person_id": "fixture_curated_joint_ingest_01",
                "name": "Test Person",
                "dob_utc": "1990-06-15T00:00:00Z",
                "iana_tz": "Asia/Seoul",
                "is_male": False,
                "source_url": "https://example.com/verified-source",
                "source_citation": "Example Citation 2020",
                "provenance": "test_fixture",
                "note": "[FACT] pytest",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    tgt = tmp_path / "out.jsonl"

    fake_birth = {
        "full_saju": {"saju": {"year": "庚", "month": "午", "day": "子", "hour": "丙"}},
        "resolution": {"ok": True},
    }

    def fake_run(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(  # type: ignore[call-arg]
            args=(),
            returncode=0,
            stdout=json.dumps(fake_birth, ensure_ascii=False) + "\n",
            stderr="",
        )

    code, summary = _run_ingest_main(inp, tgt, fake_run=fake_run)
    assert code == 0, summary
    assert summary.get("appended") == 1
    assert tgt.is_file()
    line = tgt.read_text(encoding="utf-8").strip()
    row = json.loads(line)
    assert row["schema"] == "sasang_saju_joint_benchmark_row_v1"
    assert row["person_id"] == "fixture_curated_joint_ingest_01"
    assert row["benchmark_tier"] == "curated_saju_joint_v1"
    assert row["saju_engine_output_v1"]["pillars"]["year"] == "庚"


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    inp = tmp_path / "in.jsonl"
    inp.write_text(
        json.dumps(
            {
                "dob_utc": "1990-06-15T00:00:00Z",
                "iana_tz": "Asia/Seoul",
                "is_male": True,
                "provenance_url": "https://example.com/p",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    tgt = tmp_path / "out.jsonl"
    fake_birth = {
        "full_saju": {"saju": {"year": "甲", "month": "子", "day": "子", "hour": "甲"}},
        "resolution": {},
    }

    def fake_run(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(  # type: ignore[call-arg]
            args=(),
            returncode=0,
            stdout=json.dumps(fake_birth, ensure_ascii=False) + "\n",
            stderr="",
        )

    code, summary = _run_ingest_main(inp, tgt, dry_run=True, fake_run=fake_run)
    assert code == 0
    assert summary.get("dry_run") is True
    assert not tgt.exists() or tgt.read_text(encoding="utf-8").strip() == ""
