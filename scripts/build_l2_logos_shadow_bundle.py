#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emit L2 Logos Shadow bundle JSON (Track A / Track B side-by-side, no fusion).

Read-only with respect to Logos/market pipelines: only writes the shadow report file.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


SPEC_VERSION = "l2_logos_shadow_v0.1"


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug_episode(episode_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", episode_id.strip())
    return s.strip("_")[:120] or "episode"


def _validate_status(s: str) -> str:
    if s not in ("pending", "ok"):
        raise ValueError("--track-a-status must be pending or ok")
    return s


def build_bundle(
    episode_id: str,
    track_a_pointers: List[str],
    track_a_status: str,
    track_b_label: str,
    track_b_pointers: List[str],
    primary_regime_narrative: str,
) -> Dict[str, Any]:
    return {
        "spec_version": SPEC_VERSION,
        "episode_id": episode_id.strip(),
        "generated_at_utc": _utc_iso(),
        "track_a_logos": {
            "status": track_a_status,
            "pointer_paths": list(track_a_pointers),
            "note": "Root 전용; 시장 입력 없음",
        },
        "track_b_episode": {
            "label_human": track_b_label.strip(),
            "fact_pointers": list(track_b_pointers),
            "primary_regime_narrative": primary_regime_narrative.strip(),
            "disclaimer": (
                "1차 레짐=실물 테이블 기준 아님·문서/내러티브 라벨만; "
                "실전 시그널·트리거 금지(헌법 보조축)."
            ),
        },
        "junction": {
            "mode": "side_by_side_only",
            "forbidden": ["single_field_fusion", "verse_plus_ohlc_same_prompt"],
        },
    }


def _optional_verify_paths(paths: List[str], workspace: Path) -> List[str]:
    missing: List[str] = []
    for p in paths:
        raw = p.strip()
        if not raw:
            continue
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = workspace / raw
        if not candidate.exists():
            missing.append(raw)
    return missing


def main() -> int:
    wr = _workspace_root()
    ap = argparse.ArgumentParser(
        description="Build L2 Logos Shadow bundle JSON (Track A/B 격벽, side-by-side)."
    )
    ap.add_argument(
        "--episode-id",
        default="mkt_2020-03_covid_shock_v1",
        help="Internal episode id (default: pilot KOSPI/global shock axis).",
    )
    ap.add_argument(
        "--track-a-status",
        choices=("pending", "ok"),
        default="pending",
        help="Track A completion status.",
    )
    ap.add_argument(
        "--track-a-pointer",
        action="append",
        default=[],
        metavar="PATH",
        help="Repeatable: Logos/root artifact path (file or dir).",
    )
    ap.add_argument(
        "--track-b-label",
        default="2020-03 global risk-off / KOSPI shock (pilot)",
        help="Human-readable episode label for Track B.",
    )
    ap.add_argument(
        "--track-b-pointer",
        action="append",
        default=[],
        metavar="PATH",
        help="Repeatable: fact/report pointer for Track B.",
    )
    ap.add_argument(
        "--primary-regime-narrative",
        default="historic_name_only_placeholder",
        help="Narrative regime label only (not live regime table).",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path(
            os.environ.get("L2_SHADOW_OUT_DIR", str(wr / "reports" / "l2"))
        ),
        help="Output directory (default: reports/l2 or L2_SHADOW_OUT_DIR).",
    )
    ap.add_argument(
        "--require-existing-pointers",
        action="store_true",
        help="Fail if any pointer path does not exist under workspace resolution.",
    )
    ap.add_argument(
        "--stdout",
        action="store_true",
        help="Print JSON to stdout only (still writes file unless --stdout-only).",
    )
    ap.add_argument(
        "--stdout-only",
        action="store_true",
        help="Print JSON to stdout; do not write files.",
    )
    args = ap.parse_args()

    track_a_status = _validate_status(args.track_a_status)
    bundle = build_bundle(
        episode_id=args.episode_id,
        track_a_pointers=list(args.track_a_pointer or []),
        track_a_status=track_a_status,
        track_b_label=args.track_b_label,
        track_b_pointers=list(args.track_b_pointer or []),
        primary_regime_narrative=args.primary_regime_narrative,
    )

    all_pointers = bundle["track_a_logos"]["pointer_paths"] + bundle["track_b_episode"][
        "fact_pointers"
    ]
    if args.require_existing_pointers:
        missing = _optional_verify_paths(all_pointers, wr)
        if missing:
            print(json.dumps({"error": "missing_pointers", "paths": missing}, ensure_ascii=False))
            return 3

    text = json.dumps(bundle, ensure_ascii=False, indent=2)

    if args.stdout or args.stdout_only:
        print(text)

    if args.stdout_only:
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = _slug_episode(args.episode_id)
    out_path = out_dir / f"l2_logos_shadow_{slug}_{stamp}.json"
    latest = out_dir / "l2_logos_shadow_latest.json"

    out_path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(f"Wrote: {out_path}", flush=True)
    print(f"Wrote: {latest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
