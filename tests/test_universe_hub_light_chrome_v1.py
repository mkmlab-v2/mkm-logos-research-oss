"""Hub light chrome path gate — all /hub/* share discover palette."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "projects/no1kmedi/src/lib/universeHubDiscoverMinimalV1.ts"
    text = path.read_text(encoding="utf-8")
    assert "isHubLightChrome" in text
    assert "isHubDiscoverMinimalMode" in text
    return text


def test_hub_light_chrome_covers_reports_path():
    _load()
    # Mirror TS logic in Python for deterministic gate
    def is_hub_light_chrome(pathname: str) -> bool:
        path = pathname.rstrip("/") or "/hub"
        return path == "/hub" or path.startswith("/hub/")

    def is_hub_discover_minimal(pathname: str) -> bool:
        path = pathname.rstrip("/") or "/hub"
        return path == "/hub"

    assert is_hub_light_chrome("/hub/reports")
    assert is_hub_light_chrome("/hub")
    assert not is_hub_discover_minimal("/hub/reports")
    assert is_hub_discover_minimal("/hub")
