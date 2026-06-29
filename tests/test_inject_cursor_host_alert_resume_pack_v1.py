from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import inject_cursor_host_alert_resume_pack_v1 as mod


def test_inject_prepends_banner_when_degraded(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    reports = root / "reports"
    reports.mkdir()
    art = root / "docs/final/artifacts"
    art.mkdir(parents=True)

    (reports / "cursor_host_hygiene_latest.json").write_text(
        json.dumps(
            {
                "schema": "cursor_host_hygiene_v1",
                "degraded": True,
                "reload_required": True,
                "reasons": ["state.vscdb 54GB >= warn 30GB"],
            }
        ),
        encoding="utf-8",
    )
    pack = art / "mkm_chat_resume_pack_latest.md"
    pack.write_text("# MKM Chat Resume Pack\n\nbody\n", encoding="utf-8")

    monkeypatch.setattr(mod, "ROOT", root)
    monkeypatch.setattr(mod, "PACK_MD", pack)
    monkeypatch.setattr(mod, "HYGIENE_JSON", reports / "cursor_host_hygiene_latest.json")
    monkeypatch.setattr(mod, "DEGRADED_JSON", reports / "cursor_perf_degraded.json")

    assert mod.main() == 0
    text = pack.read_text(encoding="utf-8")
    assert text.startswith("> **[!] ATTENTION: Cursor Reload Required**")
    assert "# MKM Chat Resume Pack" in text


def test_inject_skips_when_ok(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    reports = root / "reports"
    reports.mkdir()
    art = root / "docs/final/artifacts"
    art.mkdir(parents=True)
    (reports / "cursor_host_hygiene_latest.json").write_text(
        json.dumps({"schema": "cursor_host_hygiene_v1", "degraded": False}),
        encoding="utf-8",
    )
    pack = art / "mkm_chat_resume_pack_latest.md"
    pack.write_text("# MKM Chat Resume Pack\n", encoding="utf-8")

    monkeypatch.setattr(mod, "ROOT", root)
    monkeypatch.setattr(mod, "PACK_MD", pack)
    monkeypatch.setattr(mod, "HYGIENE_JSON", reports / "cursor_host_hygiene_latest.json")
    monkeypatch.setattr(mod, "DEGRADED_JSON", reports / "cursor_perf_degraded.json")

    assert mod.main() == 0
    assert pack.read_text(encoding="utf-8") == "# MKM Chat Resume Pack\n"
