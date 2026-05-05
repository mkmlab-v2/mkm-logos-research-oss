#!/usr/bin/env python3
"""Assemble B-Track LLM input bundle from independent lens + fusion stub artifacts (read-only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"

DEFAULT_MYEONGNI = ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
DEFAULT_SASANG = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
DEFAULT_LOGOS = ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"
DEFAULT_FUSION = ROOT / "docs/final/artifacts/independent_lens_fusion_stub_latest.json"
DEFAULT_MINORITY_MONTHLY = ROOT / "docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json"
DEFAULT_NEWS_LENS = ROOT / "docs/final/artifacts/news_independent_lens_latest.json"
DEFAULT_MACRO_LENS = ROOT / "docs/final/artifacts/macro_independent_lens_latest.json"


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build btrack_llm_input_bundle_latest.json for LLM hypothesis step.")
    ap.add_argument("--myeongni", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--sasang", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--logos", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--fusion", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--minority-monthly", type=Path, default=DEFAULT_MINORITY_MONTHLY)
    ap.add_argument("--news-lens", type=Path, default=DEFAULT_NEWS_LENS, help="news_independent_lens JSON (adapter output)")
    ap.add_argument("--macro-lens", type=Path, default=DEFAULT_MACRO_LENS, help="macro_independent_lens JSON (adapter output)")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bundle = {
        "schema": "btrack_llm_input_bundle_v1",
        "version": "1.1.0",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "label": "[HYPO] LLM input bundle — not A-track; no live trigger.",
        "artifacts": {
            "myeongni_independent_lens": _read(args.myeongni),
            "sasang_independent_lens": _read(args.sasang),
            "logos_independent_lens": _read(args.logos),
            "independent_lens_fusion_stub": _read(args.fusion),
            "independent_lens_shadow_minority_monthly": _read(args.minority_monthly),
            "news_independent_lens": _read(args.news_lens),
            "macro_independent_lens": _read(args.macro_lens),
        },
        "artifact_paths": {
            "myeongni": str(args.myeongni.resolve()),
            "sasang": str(args.sasang.resolve()),
            "logos": str(args.logos.resolve()),
            "fusion": str(args.fusion.resolve()),
            "independent_lens_shadow_minority_monthly": str(args.minority_monthly.resolve()),
            "news_independent_lens": str(args.news_lens.resolve()),
            "macro_independent_lens": str(args.macro_lens.resolve()),
        },
        "note": "Feed summarized fields to LLM; do not merge with live trading. Sasang: [NON-MEDICAL] if referenced. "
        "news/macro slots filled when news_independent_lens_latest.json / macro_independent_lens_latest.json exist "
        "(run build_btrack_news_macro_lens_adapters_v1.py).",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
