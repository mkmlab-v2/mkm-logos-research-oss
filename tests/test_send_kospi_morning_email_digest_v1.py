"""Morning KOSPI email digest — dry-run and gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import send_kospi_morning_email_digest_v1 as email_mod  # noqa: E402


def _seed_kospi_artifacts(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "internal_kospi_morning_brief_onepager_latest.json").write_text(
        json.dumps(
            {
                "today_action": "HOLD",
                "confidence_0_100": 40,
                "market_session_ko": "휴장(주말)",
                "dual_leg_kospi_n_evaluated": 15,
                "dual_leg_kospi_hit_rate": 0.533333,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (art / "trackc_prophecy_dual_leg_brief_latest.json").write_text("{}", encoding="utf-8")
    (art / "btrack_hypothesis_prophecy_latest.json").write_text(
        json.dumps({"prediction": {"instrument": "kospi", "direction": "bull", "confidence": 0.71}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "prophecy_hit_rate_eval_latest.json").write_text("{}", encoding="utf-8")


def test_default_recipient_falls_back_to_gmail(monkeypatch) -> None:
    monkeypatch.delenv("MKM_KOSPI_MORNING_EMAIL_TO", raising=False)
    monkeypatch.delenv("MKM_MKMLIFE_SUPPORT_FORWARD_TO", raising=False)
    assert email_mod._default_recipient() == "moksorinw@gmail.com"


def test_email_digest_skipped_when_disabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MKM_KOSPI_MORNING_EMAIL_ENABLED", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["send_kospi_morning_email_digest_v1.py", "--workspace-root", str(tmp_path)],
    )
    assert email_mod.main() == 0


def test_email_digest_dry_run_writes_preview(monkeypatch, tmp_path: Path) -> None:
    _seed_kospi_artifacts(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "send_kospi_morning_email_digest_v1.py",
            "--workspace-root",
            str(tmp_path),
            "--dry-run",
            "--force",
        ],
    )
    assert email_mod.main() == 0
    preview = tmp_path / "reports" / "kospi_morning_email_digest_preview_latest.txt"
    assert preview.is_file()
    text = preview.read_text(encoding="utf-8")
    assert "MKM 장전 코스피" in text
    assert "관망" in text
