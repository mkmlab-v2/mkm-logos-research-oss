"""mkmlife skim-read preference resolver (mirrors lib/mkmlife-skim-read-v1.ts)."""

from __future__ import annotations

from typing import Literal, Optional

SkimViewMode = Literal["skim", "full"]


def parse_skim_view_mode(value: Optional[str]) -> Optional[SkimViewMode]:
    if value in ("skim", "full"):
        return value  # type: ignore[return-value]
    return None


def resolve_skim_view_mode(
    url_param: Optional[str],
    storage_mode: Optional[SkimViewMode] = None,
    default_mode: SkimViewMode = "skim",
) -> SkimViewMode:
    return parse_skim_view_mode(url_param) or storage_mode or default_mode


def test_parse_skim_view_mode() -> None:
    assert parse_skim_view_mode("skim") == "skim"
    assert parse_skim_view_mode("full") == "full"
    assert parse_skim_view_mode("invalid") is None
    assert parse_skim_view_mode(None) is None


def test_resolve_skim_view_mode_priority() -> None:
    assert resolve_skim_view_mode("full", "skim") == "full"
    assert resolve_skim_view_mode(None, "full") == "full"
    assert resolve_skim_view_mode(None, None) == "skim"
    assert resolve_skim_view_mode("nope", "full") == "full"
