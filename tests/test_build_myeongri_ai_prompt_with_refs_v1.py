# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


def test_prompt_builder_stdout_and_recommendation_file(tmp_path: Path) -> None:
    from scripts.build_myeongri_ai_prompt_with_refs_v1 import main

    det = tmp_path / "det.json"
    det.write_text('{"axis":"myeongri"}', encoding="utf-8")
    out = tmp_path / "rec.json"

    import sys

    argv = [
        "build_myeongri_ai_prompt_with_refs_v1.py",
        "--profile",
        "daewoon",
        "--deterministic-json",
        str(det),
        "--recommendation-out",
        str(out),
    ]
    old = sys.argv
    sys.argv = argv
    try:
        rc = main()
    finally:
        sys.argv = old

    assert rc == 0
    assert out.is_file()
    content = out.read_text(encoding="utf-8")
    assert "myeongri_external_reference_recommendation_v1" in content
