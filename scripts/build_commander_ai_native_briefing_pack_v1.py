#!/usr/bin/env python3
"""Build AI-native internal briefing pack: summary MD + card news + podcast script."""

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
DEFAULT_BRIEF_MD = ART / "commander_ai_native_briefing_latest.md"
DEFAULT_CARD_MD = ART / "commander_ai_native_card_news_latest.md"
DEFAULT_PODCAST_MD = ART / "commander_ai_native_podcast_script_latest.md"
DEFAULT_OUT_JSON = ART / "commander_ai_native_briefing_pack_latest.json"


def _card_lines(items: list[dict[str, Any]], *, max_cards: int = 5) -> list[str]:
    lines = ["## AI 네이티브 카드뉴스 (내부 초안)", ""]
    for idx, item in enumerate(items[:max_cards], start=1):
        hook = f"사람들이 실제로 반응한 {item.get('platform', '콘텐츠')} 패턴"
        lines.extend(
            [
                f"### 카드 {idx}",
                f"- **주제**: {item.get('topic_label_ko', item.get('topic_id', '—'))}",
                f"- **한 줄**: {item.get('title', '—')}",
                f"- **훅**: {hook}",
                f"- **지표**: score {item.get('engagement_score', '—')} · 👍 {item.get('likes', 0)} · 💬 {item.get('comments', 0)}",
                f"- **벤치마킹**: 톤·포맷만 참고 — 그대로 복붙·대외 게시 금지",
                "",
            ]
        )
    return lines


def _podcast_script(items: list[dict[str, Any]], *, date_label: str) -> list[str]:
    top = items[:3]
    lines = [
        f"# AI 네이티브 뉴스 브리핑 팟캐스트 대본 · {date_label}",
        "",
        "**진행**: 밝고 친근한 톤 (내부 청취용) · **길이**: 약 3분",
        "",
        "## 오프닝",
        "안녕하세요. 이번 주 관심 분야에서 사람들이 실제로 반응한 신호만 골라 전달드립니다. "
        "인기가 곧 정답은 아니니, 벤치마킹 참고용으로만 들어 주세요.",
        "",
        "## 본문",
    ]
    for idx, item in enumerate(top, start=1):
        lines.extend(
            [
                f"### {idx}번 이슈 — {item.get('topic_label_ko', '주제')}",
                f"{item.get('title', '제목 없음')}. "
                f"플랫폼은 {item.get('platform', 'unknown')}이고, "
                f"좋아요 {item.get('likes', 0)}·댓글 {item.get('comments', 0)} 수준의 반응이 있었습니다. "
                "핵심은 '무엇을 할지'를 먼저 정하고, 반응 데이터는 그 다음에 보는 것입니다.",
                "",
            ]
        )
    lines.extend(
        [
            "## 클로징",
            "오늘 브리핑은 여기까지입니다. 카드뉴스 초안과 주간 벤치마크 JSON도 함께 저장해 두었으니 "
            "필요할 때만 골라 쓰시면 됩니다. 대외 게시는 사람 승인 후에만 진행해 주세요.",
            "",
            "---",
            "`internal_only` · `send_gate: HOLD` · not patient-facing",
        ]
    )
    return lines


def build_pack(weekly: dict[str, Any], *, max_cards: int = 5) -> dict[str, Any]:
    items = list(weekly.get("top_items") or [])
    date_label = str(weekly.get("generated_at_utc") or utc_now().strftime("%Y-%m-%d"))[:10]
    brief_lines = [
        "## Commander AI-Native Briefing",
        f"- `date`: `{date_label}`",
        f"- `items`: `{len(items)}`",
        "",
        "### Executive summary",
        "관심 토픽별 engagement TOP 신호를 주간 집계했습니다. "
        "도메인 판단은 지휘관, 데이터는 참고 입력입니다.",
        "",
    ]
    for idx, item in enumerate(items[:5], start=1):
        brief_lines.append(
            f"{idx}. {item.get('topic_label_ko')} — {item.get('title')} (score {item.get('engagement_score')})"
        )
    brief_md = "\n".join(brief_lines) + "\n"
    card_md = "\n".join(_card_lines(items, max_cards=max_cards)) + "\n"
    podcast_md = "\n".join(_podcast_script(items, date_label=date_label)) + "\n"
    return {
        "schema": "commander_ai_native_briefing_pack_v1",
        "generated_at_utc": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_weekly_json": weekly.get("config_path"),
        "weekly_report_generated_at_utc": weekly.get("generated_at_utc"),
        "item_count": len(items),
        "outputs": {
            "briefing_md": DEFAULT_BRIEF_MD.relative_to(ROOT).as_posix(),
            "card_news_md": DEFAULT_CARD_MD.relative_to(ROOT).as_posix(),
            "podcast_script_md": DEFAULT_PODCAST_MD.relative_to(ROOT).as_posix(),
        },
        "track_wall": weekly.get("track_wall") or {},
        "disclaimer_ko": weekly.get("disclaimer_ko") or "",
        "_md": {
            "briefing": brief_md,
            "card_news": card_md,
            "podcast_script": podcast_md,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weekly-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--max-cards", type=int, default=5)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--brief-md", type=Path, default=DEFAULT_BRIEF_MD)
    ap.add_argument("--card-md", type=Path, default=DEFAULT_CARD_MD)
    ap.add_argument("--podcast-md", type=Path, default=DEFAULT_PODCAST_MD)
    args = ap.parse_args()

    weekly_path = resolve_path(args.weekly_json)
    if not weekly_path.is_file():
        raise SystemExit(f"Missing weekly report: {weekly_path}")
    weekly = load_json(weekly_path)
    pack = build_pack(weekly, max_cards=args.max_cards)
    md_parts = pack.pop("_md")

    for path_key, content in (
        (args.brief_md, md_parts["briefing"]),
        (args.card_md, md_parts["card_news"]),
        (args.podcast_md, md_parts["podcast_script"]),
    ):
        out = resolve_path(path_key)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")

    out_json = resolve_path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out_json": str(out_json),
                "brief_md": str(resolve_path(args.brief_md)),
                "card_md": str(resolve_path(args.card_md)),
                "podcast_md": str(resolve_path(args.podcast_md)),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
