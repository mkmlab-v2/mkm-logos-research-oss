"""LLM Wiki / OKF thin lint — happy + fail + synthesizer smoke (CI-friendly)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LINT_SCRIPT = ROOT / "scripts" / "check_llm_wiki_lint_v1.py"
SYNTH_SCRIPT = ROOT / "scripts" / "synthesize_llm_wiki_theory_mathematization_v1.py"


def _load_lint_mod():
    spec = importlib.util.spec_from_file_location("check_llm_wiki_lint_v1", LINT_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def lint_mod():
    return _load_lint_mod()


def _write_md(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_lint_happy_wiki_yaml(tmp_path: Path, lint_mod) -> None:
    md = _write_md(
        tmp_path / "wiki_ok.md",
        """---
schema: llm_wiki_wiki_v1
type: Theory Canon
content_type: synthesis
title: Happy wiki
timestamp: 2026-07-13T00:00:00Z
grade: HYPO
track: B-track internal
---

Body.
""",
    )
    row = lint_mod.lint_file(md, strict=False)
    assert row["ok"] is True
    assert row["status"] == "ok"
    assert row["errors"] == []
    assert row["content_type"] == "synthesis"


def test_lint_fail_missing_required(tmp_path: Path, lint_mod) -> None:
    md = _write_md(
        tmp_path / "wiki_bad.md",
        """---
schema: llm_wiki_wiki_v1
content_type: synthesis
---

Missing type/title/grade/track/timestamp.
""",
    )
    row = lint_mod.lint_file(md, strict=False)
    assert row["ok"] is False
    assert row["status"] == "fail"
    errs = set(row["errors"])
    assert "missing:type" in errs
    assert "missing:title" in errs
    assert "missing:timestamp_or_generated_at_utc" in errs
    assert "missing:grade" in errs
    assert "missing:track" in errs


def test_lint_fail_bad_content_type(tmp_path: Path, lint_mod) -> None:
    md = _write_md(
        tmp_path / "wiki_bad_ct.md",
        """---
schema: llm_wiki_wiki_v1
type: Theory Canon
content_type: not_a_real_type
title: Bad CT
timestamp: 2026-07-13T00:00:00Z
grade: HYPO
track: B-track internal
---

Body.
""",
    )
    row = lint_mod.lint_file(md, strict=False)
    assert row["ok"] is False
    assert "bad_content_type:not_a_real_type" in row["errors"]


def test_lint_legacy_no_yaml_skipped(tmp_path: Path, lint_mod) -> None:
    md = _write_md(
        tmp_path / "legacy.md",
        "# Legacy pointer\n\nNo YAML frontmatter.\n",
    )
    row = lint_mod.lint_file(md, strict=False)
    assert row["ok"] is True
    assert row["status"] == "skipped_legacy_no_yaml"
    assert "no_yaml_frontmatter" in row["warnings"]


def test_repo_lint_cli_exit_0() -> None:
    proc = subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--stdout-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload.get("ok") is True
    assert payload.get("error_count") == 0


def test_l1_to_l0_mirror_wall_ok(lint_mod) -> None:
    wall = lint_mod.check_l1_to_l0_mirror_wall(ROOT)
    assert wall["ok"] is True, wall.get("errors")
    assert wall["auto_mirror_forbidden"] is True
    assert wall["allowed_l0_writer"] == "scripts/athena_checkpoint.py"
    assert wall["producer_checkpoint_hits"] == []


def test_synthesize_theory_wiki_smoke() -> None:
    if not (ROOT / "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md").is_file():
        pytest.skip("theory canon artifact missing")
    proc = subprocess.run(
        [sys.executable, str(SYNTH_SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report_path = ROOT / "docs/final/artifacts/llm_wiki_theory_mathematization_synthesis_v1_latest.json"
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report.get("ok") is True
    wiki = ROOT / report["wiki_path"]
    assert wiki.is_file()
    text = wiki.read_text(encoding="utf-8")
    assert "schema: llm_wiki_wiki_v1" in text
    assert "content_type: synthesis" in text
    assert "ops_memory_pin_ids:" in text
