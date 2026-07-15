# -*- coding: utf-8 -*-
"""Regression: athena_checkpoint prepends without wiping prior bullets."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "athena_checkpoint.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("athena_checkpoint_v1", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_merge_checkpoint_inner_prepends_and_caps():
    mod = _load_mod()
    inner = "\n- **2026-01-01T00:00:00Z** — old one\n"
    out = mod._merge_checkpoint_inner(inner, "2026-02-02T00:00:00Z", "new one", max_lines=3)
    lines = out.splitlines()
    assert lines[0] == mod.CENTRAL_MARKER
    assert lines[1] == "- **2026-02-02T00:00:00Z** — new one"
    assert lines[2] == "- **2026-01-01T00:00:00Z** — old one"


def test_merge_checkpoint_inner_trims_oldest_when_over_cap():
    mod = _load_mod()
    inner = "\n".join(
        f"- **2026-01-0{i}T00:00:00Z** — line{i}"
        for i in range(1, 6)  # 5 old bullets
    )
    out = mod._merge_checkpoint_inner(inner, "2026-12-12T00:00:00Z", "fresh", max_lines=3)
    lines = out.splitlines()
    assert len(lines) == 4
    assert lines[0] == mod.CENTRAL_MARKER
    assert "fresh" in lines[1]
    assert "line1" in lines[2]
    assert "line2" in lines[3]
    assert "line3" not in out


def test_replace_checkpoint_default_merges():
    mod = _load_mod()
    start = mod.MARK_START
    end = mod.MARK_END
    content = f"""# x

{start}
- **t1** — first
{end}

tail
"""
    updated = mod._replace_checkpoint(
        content,
        "t2",
        "second",
        replace_all=False,
        max_checkpoints=10,
    )
    assert "- **t2** — second" in updated
    assert "- **t1** — first" in updated
    assert updated.index("t2") < updated.index("t1")


def test_replace_checkpoint_replace_all_single_line():
    mod = _load_mod()
    start = mod.MARK_START
    end = mod.MARK_END
    content = f"""{start}
- **old** — gone
{end}
"""
    updated = mod._replace_checkpoint(
        content,
        "new",
        "only",
        replace_all=True,
        max_checkpoints=10,
    )
    assert "- **new** — only" in updated
    assert "gone" not in updated


def test_merge_checkpoint_inner_same_continuity_burst_replaces_not_prepends():
    mod = _load_mod()
    inner = (
        "\n"
        "- **2026-07-15T07:43:48Z** — continuity=demo-burst · homepage LIVE DONE deploy exit0\n"
    )
    out = mod._merge_checkpoint_inner(
        inner,
        "2026-07-15T07:44:02Z",
        "continuity=demo-burst · homepage live DONE; next Paddle",
        max_lines=5,
        same_continuity_burst_seconds=60,
    )
    lines = out.splitlines()
    assert len(lines) == 2
    assert lines[0] == mod.CENTRAL_MARKER
    assert "07:44:02" in lines[1]
    assert "next Paddle" in lines[1]
    assert "07:43:48" not in out
