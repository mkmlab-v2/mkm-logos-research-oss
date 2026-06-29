#!/usr/bin/env python3
"""Morning Telegram — single maximum-insight report only (one message).

Default SSOT: reports/logos_2026_ai_industry_max_util_insight_v1_latest.md
Override: MKM_TELEGRAM_MAX_INSIGHT_REPORT_PATH

No separate prophecy/Brier/gate blocks in the same send. Commander trades; agent observes only.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
REPORTS = ROOT / "reports"
TELEGRAM_MAX = 4096
DEFAULT_REPORT = REPORTS / "logos_2026_ai_industry_max_util_insight_v1_latest.md"
POSITION_PATH = REPORTS / "commander_btc_position_observation_latest.json"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _report_path(workspace: Path) -> Path:
    env = os.getenv("MKM_TELEGRAM_MAX_INSIGHT_REPORT_PATH", "").strip()
    if env:
        p = Path(env)
        return p if p.is_absolute() else workspace / p
    return workspace / "reports" / "logos_2026_ai_industry_max_util_insight_v1_latest.md"


def _extract_section(md: str, heading: str) -> str:
    """Extract body under ## N. title until next ##."""
    pattern = rf"^##\s*{re.escape(heading)}\s*$"
    lines = md.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line.strip(), re.IGNORECASE):
            start = i + 1
            break
    if start is None:
        return ""
    out: List[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.strip() == "---":
            continue
        s = line.strip()
        if s.startswith("|") and "---" in s:
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.split("|") if c.strip()]
            if cells and not all(set(c) <= {"-"} for c in cells):
                out.append(" · ".join(cells[:4]))
            continue
        if s.startswith("```"):
            continue
        if s.startswith("#"):
            s = s.lstrip("#").strip()
        out.append(s)
    return "\n".join(x for x in out if x).strip()


def _compress_insights(section4: str) -> str:
    lines: List[str] = []
    for block in re.split(r"\n###\s+", section4):
        block = block.strip()
        if not block.startswith("통찰"):
            continue
        first = block.split("\n", 1)[0].strip()
        body = ""
        if "\n" in block:
            body = block.split("\n", 1)[1].strip().split("\n")[0][:180]
        lines.append(f"  {first}" + (f" — {body}" if body else ""))
    return "\n".join(lines[:5])


def _md_to_single_report(workspace: Path, report_path: Path) -> str:
    md = report_path.read_text(encoding="utf-8-sig")
    s0 = _extract_section(md, "0. 한 줄 요약") or _extract_section(md, "0")
    s1 = _extract_section(md, "1. Field → Lens → Conflict → Final Action") or _extract_section(md, "1")
    s4 = _extract_section(md, "4. AI 산업 5대 통찰 (최대 활용 합성)") or _extract_section(md, "4")
    s8 = _extract_section(md, "8. 한계 (Fact-Lock)") or _extract_section(md, "8")

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    title = "📋 MKM 최대통찰 보고서"
    if "AI 산업" in md[:200]:
        title += " · AI·반도체·Logos"

    parts = [
        f"{title} · {now_kst}",
        "역할: 지휘관 매매 · 에이전트 관측만 · 텔레그램 1통=본 보고서만",
        "[HYPO] B-track · Logos [NON_GATING] · 매매·Track A 합선 없음",
        "",
        "━━ 한 줄 ━━",
        s0 or "(요약 없음)",
        "",
        "━━ Field→Lens→Final ━━",
    ]
    if s1:
        for ln in s1.split("\n")[:12]:
            parts.append(f"  {ln[:240]}")
    else:
        parts.append("  (본문 없음)")

    if s4:
        parts.extend(["", "━━ 통찰 5선 ━━", _compress_insights(s4)])

    btc = _read_json(workspace / "reports" / "commander_btc_position_observation_latest.json")
    if btc.get("notional_usdt") is not None:
        pnl = btc.get("unrealized_pnl_pct")
        parts.extend(
            [
                "",
                "━━ 지휘관 BTC(관측 1줄·본문과 별도 트리거 아님) ━━",
                f"  노출 ~{float(btc['notional_usdt']):.0f} USDT · 미실현 {pnl}%" if pnl is not None else f"  노출 ~{float(btc['notional_usdt']):.0f} USDT",
            ]
        )

    if s8:
        parts.extend(["", "━━ 한계 ━━"])
        for ln in s8.split("\n")[:4]:
            if ln.strip().startswith("-"):
                parts.append(f"  {ln.strip()[1:].strip()[:200]}")

    parts.append("")
    parts.append(f"SSOT: {report_path.name}")
    return "\n".join(parts)


def build_morning_insight_max_text(workspace: Path = ROOT, *, max_len: int = TELEGRAM_MAX) -> str:
    """One Telegram message = one max-insight report (MD SSOT), not a multi-digest combo."""
    report_path = _report_path(workspace.resolve())
    if not report_path.is_file():
        return (
            f"📋 MKM 최대통찰 보고서 · {datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')}\n"
            f"(보고서 없음: {report_path})\n"
            "[HYPO] reports/logos_2026_ai_industry_max_util_insight_v1_latest.md 생성 후 재전송"
        )

    text = _md_to_single_report(workspace.resolve(), report_path)
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 40].rstrip()
    return cut + "\n…(길이 제한·SSOT MD 참고)"


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=REPORTS / "telegram_morning_insight_max_preview_latest.txt")
    args = ap.parse_args()
    text = build_morning_insight_max_text(args.workspace_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"WROTE: {args.out} chars={len(text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
