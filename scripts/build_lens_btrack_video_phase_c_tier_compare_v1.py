#!/usr/bin/env python3
"""FFprobe tier compare report: production PIL vs AnimateDiff smoke|mq|hq|hybrid."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/track_c_video_hook_samples_v1/phase_c_hypo_v1"
PROD_WEBM = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/.showroom_staging/video/lens_btrack/v1"
)


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _probe(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=width,height,codec_name",
            "-show_entries",
            "format=duration,size,bit_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"path": str(path), "error": (proc.stderr or "")[-400:]}
    data = json.loads(proc.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "codec": stream.get("codec_name"),
        "duration_sec": float(fmt.get("duration") or 0),
        "size_bytes": int(fmt.get("size") or 0),
        "bit_rate": int(fmt.get("bit_rate") or 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hypo-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--pairs",
        nargs="*",
        default=["taeyang:idle", "soeum:attack"],
        metavar="SASANG:MODE",
        help="Pairs as sasang:mode (default taeyang:idle soeum:attack)",
    )
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    parsed_pairs: list[tuple[str, str]] = []
    for item in args.pairs:
        if isinstance(item, tuple):
            parsed_pairs.append(item)
            continue
        s, _, m = str(item).partition(":")
        parsed_pairs.append((s.strip().lower(), m.strip().lower() or "idle"))

    rows: list[dict[str, object]] = []
    for sasang, mode in parsed_pairs:
        prod = PROD_WEBM / f"lv_hp050_{sasang}_{mode}_v1.webm"
        row: dict[str, object] = {
            "sasang_primary": sasang,
            "showroom_display_mode": mode,
            "production_pil": _probe(prod),
            "animatediff": {},
        }
        ad: dict[str, object] = {}
        for tier in ("smoke", "mq", "hq"):
            p = args.hypo_dir / f"lv_hp050_{sasang}_{mode}_v1_animatediff_{tier}.webm"
            hit = _probe(p)
            if hit is None and tier == "smoke":
                legacy = args.hypo_dir / f"lv_hp050_{sasang}_{mode}_v1_animatediff_hypo.webm"
                hit = _probe(legacy)
            if hit is None and tier == "mq":
                legacy_mq = args.hypo_dir / f"lv_hp050_{sasang}_{mode}_v1_animatediff_hypo_mq.webm"
                hit = _probe(legacy_mq)
            ad[tier] = hit
        ad["pil_hybrid_mq"] = _probe(
            args.hypo_dir / f"lv_hp050_{sasang}_{mode}_v1_animatediff_mq_pil_hybrid.webm"
        )
        row["animatediff"] = ad
        rows.append(row)

    report = {
        "schema": "lens_btrack_video_phase_c_tier_compare_v1",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "generated_at_utc": _utc_now_z(),
        "rows": rows,
        "note": "production_pil = showroom LUT; animatediff tiers are research-only",
    }
    out = args.out_json or (args.hypo_dir / "lens_btrack_video_phase_c_tier_compare_v1_latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[tier-compare] WROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
