"""Passive KOSPI morning email digest gate."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_kospi_morning_email_digest_passive_v1 as passive  # noqa: E402

KST = ZoneInfo("Asia/Seoul")


def test_skips_before_0830_kst(tmp_path: Path) -> None:
    art = tmp_path / "digest.json"
    art.write_text(
        json.dumps({"ok": True, "generated_at_kst": "2020-01-01T09:00:00+09:00"}, ensure_ascii=False),
        encoding="utf-8",
    )
    now = datetime(2026, 6, 18, 8, 0, tzinfo=KST)
    report = passive.evaluate(art, now_kst=now, force=False)
    assert report["status"] == "skipped"
    assert report["ok"] is True


def test_passes_when_today_ok(tmp_path: Path) -> None:
    art = tmp_path / "digest.json"
    art.write_text(
        json.dumps(
            {"ok": True, "result": "gmail_smtp_sent", "generated_at_kst": "2026-06-18T08:28:05+09:00"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    now = datetime(2026, 6, 18, 9, 0, tzinfo=KST)
    report = passive.evaluate(art, now_kst=now, force=False)
    assert report["status"] == "pass"
    assert report["ok"] is True


def test_fails_when_stale(tmp_path: Path) -> None:
    art = tmp_path / "digest.json"
    art.write_text(
        json.dumps({"ok": True, "generated_at_kst": "2026-06-17T08:28:05+09:00"}, ensure_ascii=False),
        encoding="utf-8",
    )
    now = datetime(2026, 6, 18, 9, 0, tzinfo=KST)
    report = passive.evaluate(art, now_kst=now, force=True)
    assert report["status"] == "fail"
    assert report["ok"] is False
