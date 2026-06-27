"""Tests for compression contributions manifest checker."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/compression/contributions/compression_contributions_manifest_v1.json"
SCRIPT = ROOT / "scripts/check_compression_contributions_manifest_v1.py"
EXAMPLE = ROOT / "data/compression/examples/compression_contributor_example_v1.jsonl"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def test_empty_manifest_passes(tmp_path: Path) -> None:
    empty_contributions = tmp_path / "contributions"
    empty_contributions.mkdir()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["contributions_dir"] = str(empty_contributions.resolve())
    manifest["entries"] = []
    man_path = tmp_path / "manifest.json"
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = tmp_path / "check.json"
    proc = _run("--manifest", str(man_path), "--out-json", str(out))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["check_ok"] is True
    assert doc["on_disk_jsonl_count"] == 0


def test_validate_reference_example(tmp_path: Path) -> None:
    out = tmp_path / "check.json"
    proc = _run("--validate-reference", "--out-json", str(out))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert any(c["path"].endswith("compression_contributor_example_v1.jsonl") for c in doc["checked"])


def test_pr_strict_requires_manifest_entry(tmp_path: Path) -> None:
    corpus = tmp_path / "orphan.jsonl"
    corpus.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    contributions = tmp_path / "contributions"
    contributions.mkdir()
    corpus_in_dir = contributions / "orphan.jsonl"
    corpus_in_dir.write_text(corpus.read_text(encoding="utf-8"), encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["contributions_dir"] = str(contributions.resolve())
    manifest["entries"] = []
    man_path = tmp_path / "manifest.json"
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    proc = _run("--manifest", str(man_path), "--pr-strict", "--stdout-only")
    assert proc.returncode != 0
