"""Smoke: bulk Pack 0-B golden generator (small N; tmp dir)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA = _ROOT / "docs/final/schemas/myeongri_deterministic_lora_golden_set_v1.schema.json"
_BUILD = _ROOT / "scripts/build_myeongri_deterministic_lora_golden_bulk_v1.py"


def test_bulk_script_exists() -> None:
    assert _BUILD.is_file()


def test_bulk_generates_valid_jsonl_and_manifest(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "bulk_out"
    r = subprocess.run(
        [
            sys.executable,
            str(_BUILD),
            "--out-dir",
            str(out),
            "--seed",
            "99",
            "--train-n",
            "4",
            "--locked-eval-n",
            "2",
            "--dataset-version",
            "pytest-smoke-bulk",
            "--iana-tz",
            "Asia/Seoul",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr

    train = out / "train.jsonl"
    locked = out / "locked_eval.jsonl"
    man = out / "myeongri_deterministic_lora_golden_bulk_manifest_v1.json"
    assert train.is_file() and locked.is_file() and man.is_file()

    train_lines = [ln for ln in train.read_text(encoding="utf-8").splitlines() if ln.strip()]
    locked_lines = [ln for ln in locked.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(train_lines) == 4
    assert len(locked_lines) == 2

    for ln in train_lines + locked_lines:
        row = json.loads(ln)
        jsonschema.validate(instance=row, schema=schema)
        assert "calculated_at" not in row["expected_result"]["full_saju"]

    mdoc = json.loads(man.read_text(encoding="utf-8"))
    assert mdoc["schema"] == "myeongri_deterministic_lora_golden_bulk_manifest_v1"
    assert mdoc["train_rows"] == 4
    assert mdoc["locked_eval_rows"] == 2
    assert len(mdoc["files"]) == 2
    for f in mdoc["files"]:
        assert len(f["sha256"]) == 64
        assert f["bytes"] > 0
