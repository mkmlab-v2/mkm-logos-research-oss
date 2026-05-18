"""Smoke: finance_macro_b2b compression eval input builder (--dry-run on 2 md files when present)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_finance_macro_b2b_compression_eval_input_v1.py"
DEFAULT_MD_GLOB = ROOT / "docs" / "final" / "artifacts" / "track_c_b2b_macro*.md"


def _macro_md_files(limit: int = 2) -> list[Path]:
    if not DEFAULT_MD_GLOB.parent.is_dir():
        return []
    return sorted(p for p in DEFAULT_MD_GLOB.parent.glob(DEFAULT_MD_GLOB.name) if p.is_file())[:limit]


def test_build_finance_macro_b2b_compression_eval_input_dry_run_two_md() -> None:
    md_files = _macro_md_files(2)
    if len(md_files) < 2:
        pytest.skip("need at least 2 track_c_b2b_macro*.md under docs/final/artifacts/")

    manifest = {
        "schema": "finance_macro_b2b_compression_benchmark_manifest_v1",
        "corpus": {
            "domain_tag": "finance_macro_b2b",
            "paragraph_rules": {"min_chars": 80},
            "datasets": [
                {
                    "domain": "finance_macro_b2b",
                    "dataset_id": f"test_{i}",
                    "source_path": str(p.relative_to(ROOT)).replace("\\", "/"),
                    "format": "markdown",
                }
                for i, p in enumerate(md_files, start=1)
            ],
        },
    }

    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = Path(tmp) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--manifest",
            str(manifest_path),
            "--max-cases",
            "10",
            "--dry-run",
        ]
        cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        assert cp.returncode == 0, cp.stderr + cp.stdout
        summary = json.loads(cp.stdout.strip().splitlines()[-1])
        assert summary.get("ok") is True
        assert summary.get("dry_run") is True
        assert summary.get("case_count", 0) >= 1
