#!/usr/bin/env python3
"""Multi-theme commander digest for all LOGOS_TRACK_B_THEME_PRESETS [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs/final/artifacts"
PRESETS = ART / "LOGOS_TRACK_B_THEME_PRESETS_V1.json"
OUT_DEFAULT = REPORTS / "logos_track_b_multi_theme_commander_digest_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_optional(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return _load(path)
    except (json.JSONDecodeError, OSError):
        return None


def render() -> str:
    presets = _load(PRESETS)
    themes = presets.get("themes") or {}
    deep_doc = _load_optional(REPORTS / "logos_track_b_themed_deep_push_v1_latest.json")
    heatmap = _load_optional(REPORTS / "logos_canon_book_coverage_heatmap_v1_latest.json")
    graphrag_audit = _load_optional(REPORTS / "logos_themed_graphrag_seed_retrieval_v1_latest.json")

    lines = [
        "# Logos Track B — 멀티 테마 지휘관 다이제스트",
        "",
        "[TRACK B / HYPO] · [연구용: 최종 판단은 지휘관 대기]",
        "",
        f"> 생성 `{_utc_now()}` · NON_GATING · A-track 자동 트리거 금지",
        "",
        f"## 프리셋 테마 ({len(themes)}개)",
        "",
        "| theme_id | 제목 | citation_lock | evidence_refs |",
        "| --- | --- | --- | --- |",
    ]

    deep_by_id = {r.get("theme_id"): r for r in (deep_doc.get("themes") or []) if r.get("theme_id")}
    valid_count = 0
    for tid, theme in themes.items():
        locked = _load_optional(ART / f"logos_deep_research_distill_{tid}_citation_lock_latest.json")
        lock = (locked or {}).get("citation_lock") or {}
        locked_count = int(lock.get("locked_count") or 0)
        valid = locked_count >= 3 and locked_count >= max(1, len((locked or {}).get("evidence_refs") or []))
        if valid:
            valid_count += 1
        ev = len((locked or {}).get("evidence_refs") or [])
        lines.append(
            f"| `{tid}` | {theme.get('title_ko', tid)} | "
            f"{lock.get('locked_count', '—')} ({'valid' if valid else 'pending'}) | {ev} |"
        )

    lines += [
        "",
        f"- citation_valid: **{valid_count}/{len(themes)}**",
        "",
    ]

    if graphrag_audit:
        sm = graphrag_audit.get("summary") or {}
        lines += [
            "### GraphRAG 시드",
            "",
            f"- organic: `{sm.get('seed_hits_organic')}` · full: `{sm.get('seed_hits_full')}`",
            "",
        ]

    if heatmap:
        hm = heatmap.get("summary") or {}
        lines += [
            "### 권(book) 커버리지",
            "",
            f"- books: `{hm.get('book_count')}` · deep_validated books: `{hm.get('books_with_deep_theme')}`",
            "",
        ]

    lines += [
        "## 재현",
        "",
        "```powershell",
        "py scripts/run_logos_track_b_commercial_depth_closure_v1.py",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    md = render()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
