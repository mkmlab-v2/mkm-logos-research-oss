"""watch_submission_cover_ingest_v1 — inbox heuristics and stable-file wait."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.experimental.watch_submission_cover_ingest_v1 import (
    is_candidate_cover_pdf,
    wait_file_stable,
)


def test_rejects_draft_and_bundle_names(tmp_path: Path):
    draft = tmp_path / "opendata_327_part_a_cover_draft_v1.pdf"
    draft.write_bytes(b"x" * 2000)
    ok, reason = is_candidate_cover_pdf(draft)
    assert ok is False
    assert "draft" in reason

    bundle = tmp_path / "moksori_ai_opendata327_task1_business_plan_v1.pdf"
    bundle.write_bytes(b"x" * 2000)
    ok2, _ = is_candidate_cover_pdf(bundle)
    assert ok2 is False


def test_accepts_generic_cover_name(tmp_path: Path):
    cover = tmp_path / "kstartup_official_cover_2026.pdf"
    cover.write_bytes(b"%PDF-" + b"x" * 2000)
    ok, reason = is_candidate_cover_pdf(cover)
    assert ok is True
    assert reason == "ok"


def test_wait_file_stable_small_file(tmp_path: Path):
    p = tmp_path / "cover.pdf"
    p.write_bytes(b"x" * 5000)
    assert wait_file_stable(p, stable_seconds=0.3, poll=0.1) is True
