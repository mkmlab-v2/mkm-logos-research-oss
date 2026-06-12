"""P4 mkmlife embed URL contract mirror (TS is UI SSOT)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse


def test_mkmlife_embed_modules_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "projects/no1kmedi/src/lib/universeHubMkmlifeEmbedV2.ts").is_file()
    assert (root / "projects/no1kmedi/src/components/shell/UniverseMkmlifeEmbedV2.tsx").is_file()
    # HubEmbedChromeV1 ships in projects/mkm/mkm-life (submodule). Monorepo CI checkout
    # does not always init submodules — validate when present only.
    embed_chrome = root / "projects/mkm/mkm-life/components/HubEmbedChromeV1.tsx"
    if embed_chrome.is_file():
        assert "HubEmbedChromeV1" in embed_chrome.read_text(encoding="utf-8")


def test_build_mkmlife_embed_src_mirror():
    def build(prefill: str = "", view: str = "ask-one") -> str:
        bases = {
            "ask-one": "https://mkmlife.com/ask-one",
            "home": "https://mkmlife.com",
            "news-deck": "https://mkmlife.com/news-deck",
        }
        base = bases[view]
        sep = "&" if "?" in base else "?"
        url = f"{base}{sep}source=jema_hub_v2&embed=1"
        if prefill.strip():
            from urllib.parse import quote

            url += f"&prefill={quote(prefill.strip())}"
        return url

    parsed = urlparse(build("hello"))
    qs = parse_qs(parsed.query)
    assert qs["source"] == ["jema_hub_v2"]
    assert qs["embed"] == ["1"]
    assert qs["prefill"] == ["hello"]
