from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "check_mkmlife_pixel_sprite_urls_v1.py"


def _load_gate_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_mkmlife_pixel_sprite_urls_v1", GATE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_collect_sprite_urls_dedupes_and_includes_both_registries() -> None:
    mod = _load_gate_module()
    doc = {
        "schema": "mkm_pixel_language_v1",
        "category_sprite_registry": {
            "world": {"sprite_url": "https://cdn.example/a.png"},
            "other": {"sprite_url": "https://cdn.example/b.png"},
        },
        "morning_beans_lane_registry": {
            "field_regime": {"sprite_url": "https://cdn.example/a.png"},
            "learning": {"sprite_url": "https://cdn.example/c.png"},
        },
    }
    rows = mod.collect_sprite_urls(doc)
    urls = {r["url"] for r in rows}
    assert urls == {
        "https://cdn.example/a.png",
        "https://cdn.example/b.png",
        "https://cdn.example/c.png",
    }


def test_run_gate_fails_when_sprite_http_not_ok(tmp_path: Path) -> None:
    mod = _load_gate_module()
    pixel = tmp_path / "pixel.json"
    pixel.write_text(
        json.dumps(
            {
                "schema": "mkm_pixel_language_v1",
                "morning_beans_lane_registry": {
                    "field_regime": {"sprite_url": "https://cdn.example/bad.png"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "gate.json"

    def fake_fetch(url: str, timeout: float) -> tuple[bool, int | None, str | None]:
        if url.endswith("bad.png"):
            return False, 404, "Not Found"
        return True, 200, None

    with patch.object(mod, "_fetch_status", side_effect=fake_fetch):
        report = mod.run_gate(
            pixel_json=pixel,
            origin=None,
            origin_path="/data/MKM_PIXEL_LANGUAGE_V1.json",
            out_path=out,
            timeout=5.0,
            retries=1,
            retry_delay=0.0,
        )
    assert report["overall_ok"] is False
    assert report["fail_count"] == 1
    assert out.is_file()


def test_run_gate_local_relative_sprite_path(tmp_path: Path, monkeypatch) -> None:
    mod = _load_gate_module()
    public_root = tmp_path / "public"
    sprite_dir = public_root / "pixel_battalion" / "refined"
    sprite_dir.mkdir(parents=True)
    sprite = sprite_dir / "ok.png"
    sprite.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 64)
    monkeypatch.setattr(mod, "DEFAULT_PUBLIC_ROOT", public_root)

    pixel = tmp_path / "pixel.json"
    pixel.write_text(
        json.dumps(
            {
                "schema": "mkm_pixel_language_v1",
                "morning_beans_lane_registry": {
                    "field_regime": {"sprite_url": "/pixel_battalion/refined/ok.png"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "gate.json"
    report = mod.run_gate(
        pixel_json=pixel,
        origin=None,
        origin_path="/data/MKM_PIXEL_LANGUAGE_V1.json",
        out_path=out,
        timeout=5.0,
        retries=1,
        retry_delay=0.0,
    )
    assert report["overall_ok"] is True
    assert report["results"][0]["check_mode"] == "local"


def test_main_exit_zero_when_urls_ok(tmp_path: Path, monkeypatch) -> None:
    mod = _load_gate_module()
    pixel = tmp_path / "pixel.json"
    pixel.write_text(
        json.dumps(
            {
                "schema": "mkm_pixel_language_v1",
                "morning_beans_lane_registry": {
                    "field_regime": {"sprite_url": "https://cdn.example/ok.png"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "gate.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_mkmlife_pixel_sprite_urls_v1.py",
            "--pixel-json",
            str(pixel),
            "--out-json",
            str(out),
            "--url-retries",
            "1",
        ],
    )
    with patch.object(mod, "_fetch_status", return_value=(True, 200, None)):
        assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["overall_ok"] is True
