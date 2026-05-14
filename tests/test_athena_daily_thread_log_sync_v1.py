"""Unit tests for daily thread work log merge (no filesystem)."""

from datetime import date

import scripts.athena_daily_thread_log_sync_v1 as m


def test_merge_appends_new_thread_section() -> None:
    base = "# Log\n\n## Thread 1\n- a\n"
    out = m.merge_bullets_into_content(base, 2, ["x"])
    assert "## Thread 2" in out
    assert "- x" in out
    assert "- a" in out


def test_merge_inserts_before_next_thread() -> None:
    base = "## Thread 1\n- a\n## Thread 2\n- b\n"
    out = m.merge_bullets_into_content(base, 1, ["c"])
    # c should appear after - a and before ## Thread 2
    i_a = out.index("- a")
    i_c = out.index("- c")
    i_h2 = out.index("## Thread 2")
    assert i_a < i_c < i_h2


def test_normalize_bullets_strips_prefix() -> None:
    assert m._normalize_bullets(["  - hi  ", "* there"]) == ["hi", "there"]


def test_resolve_log_path_default_under_reports() -> None:
    d = date(2026, 5, 14)
    p = m._resolve_log_path(m.WORKSPACE_ROOT, d)
    assert p.name == "daily_thread_work_2026-05-14.md"
    assert p.parent.name == "reports"
