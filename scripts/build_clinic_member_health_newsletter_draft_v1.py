#!/usr/bin/env python3
"""Build clinic member health newsletter draft (wellness · non-diagnostic · commander relay)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from commander_interest_benchmark_v1_lib import load_json, resolve_path, utc_now  # noqa: E402

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_WEEKLY = ART / "commander_interest_benchmark_weekly_latest.json"
DEFAULT_CFG = ART / "clinic_member_health_newsletter_config_v1.default.json"
DEFAULT_OUT_MD = ART / "clinic_member_health_newsletter_draft_latest.md"
DEFAULT_OUT_JSON = ART / "clinic_member_health_newsletter_draft_latest.json"
CLINIC_TOPIC = "clinic_sns_content_benchmark"


def _date_label(weekly: dict[str, Any]) -> str:
    return str(weekly.get("generated_at_utc") or utc_now().strftime("%Y-%m-%d"))[:10]


def build_newsletter(
    weekly: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    date_label = _date_label(weekly)
    channel = str(cfg.get("channel_label_ko") or "한의원 회원")
    greeting = str(cfg.get("greeting_ko") or "").strip()
    bullets = list(cfg.get("default_wellness_bullets_ko") or [])
    disclaimer = str(cfg.get("footer_disclaimer_ko") or "").strip()
    draft_tag = str(cfg.get("draft_tag_ko") or "[DRAFT]")

    clinic_refs = [
        i
        for i in (weekly.get("top_items") or [])
        if str(i.get("topic_id") or "") == CLINIC_TOPIC
    ]

    md_lines = [
        f"# 회원 건강 뉴스레터 초안 · {date_label}",
        "",
        f"**대상:** {channel} · **용도:** 지휘관 검수 → 회원 채널 **수동** 발송",
        "",
        draft_tag,
        "",
        greeting,
        "",
        "## 이번 주 생활 건강 참고",
    ]
    for idx, bullet in enumerate(bullets[:5], start=1):
        md_lines.append(f"{idx}. {bullet}")

    if clinic_refs:
        md_lines.extend(["", "## 참고 콘텐츠 형식 (벤치마킹 · 복붙 금지)"])
        for ref in clinic_refs[:3]:
            md_lines.append(f"- {ref.get('title', '—')} ({ref.get('platform', '—')})")
            url = str(ref.get("url") or "").strip()
            if url:
                md_lines.append(f"  - {url}")

    md_lines.extend(["", "## 면책", disclaimer, "", "---", "`send_gate: HOLD` · not auto-sent to members"])

    telegram_lines = [
        f"🌿 [{channel}] 건강 뉴스레터 초안",
        draft_tag,
        "",
        greeting,
        "",
        "■ 이번 주 생활 건강 참고 (비진단)",
    ]
    for idx, bullet in enumerate(bullets[:3], start=1):
        telegram_lines.append(f"{idx}) {bullet}")

    if clinic_refs:
        telegram_lines.extend(["", "■ 참고 형식 (톤만)"])
        for ref in clinic_refs[:2]:
            telegram_lines.append(f"· {str(ref.get('title') or '—')[:100]}")

    telegram_lines.extend(["", disclaimer, "", "→ 검수 후 회원 채널에 직접 붙여넣기"])

    return {
        "schema": "clinic_member_health_newsletter_draft_v1",
        "generated_at_utc": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date_label": date_label,
        "channel_label_ko": channel,
        "clinic_reference_count": len(clinic_refs),
        "wellness_bullet_count": len(bullets[:5]),
        "track_wall": cfg.get("track_wall") or weekly.get("track_wall") or {},
        "outputs": {
            "markdown": DEFAULT_OUT_MD.relative_to(ROOT).as_posix(),
        },
        "_md": "\n".join(md_lines) + "\n",
        "_telegram": "\n".join(telegram_lines),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weekly-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--config-json", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    args = ap.parse_args()

    weekly_path = resolve_path(args.weekly_json)
    if not weekly_path.is_file():
        raise SystemExit(f"Missing weekly: {weekly_path}")
    weekly = load_json(weekly_path)
    cfg = load_json(resolve_path(args.config_json))

    doc = build_newsletter(weekly, cfg)
    md = doc.pop("_md")
    telegram = doc.pop("_telegram")
    doc["telegram_text_preview"] = telegram[:500]
    doc["telegram_char_count"] = len(telegram)

    out_md = resolve_path(args.out_md)
    out_json = resolve_path(args.out_json)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    out_json.write_text(json.dumps({**doc, "telegram_text": telegram}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out_md": str(out_md), "out_json": str(out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
