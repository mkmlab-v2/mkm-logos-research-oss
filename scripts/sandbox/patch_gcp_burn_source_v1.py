#!/usr/bin/env python3
"""Build productive Vertex burn prompt bundles (B-track only).

Lanes:
  btrack_fills_daily — daily execution features from fills cache (shadow [HYPO] labels)
  asset_rag / cross_lens / wellness_hypo / quota_stress — profile seeds (delegates)

Does NOT write Track A artifacts or trigger live trading.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FILLS_CACHE = ROOT / "reports" / "btrack_fills_daily_feature_cache_v1_latest.json"
DEFAULT_BUNDLE = ROOT / "reports" / "sandbox" / "mkm_productive_burn_bundle_v1.json"

FILLS_DAILY_TEMPLATE = (
    "[HYPO] research_only hypothesis_tier=B track_wall=btrack_research_only\n"
    "You are a shadow execution analyst (NOT ground truth). Given this BTCUSDT daily fill "
    "aggregate JSON, output JSON only with keys:\n"
    "utc_date, shadow_slippage_hypothesis, liquidity_stress_bucket, maker_taker_read, "
    "regime_guess [HYPO], limitations[], disclaimer.\n"
    "Do NOT claim causal proof or trading signals.\n\n"
    "INPUT_JSON:\n{payload}\n"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _import_profile_seeds(profile: str) -> list[str]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from run_gcp_free_trial_vertex_credit_burn_v1 import PROMPT_PROFILES

    return list(PROMPT_PROFILES.get(profile) or PROMPT_PROFILES["generic"])


def build_btrack_fills_daily_prompts(cache_path: Path, repeat: int = 1) -> list[dict[str, Any]]:
    if not cache_path.is_file():
        raise FileNotFoundError(f"missing fills cache: {cache_path}")
    cache = _load_json(cache_path)
    daily = cache.get("daily_by_utc_date")
    if not isinstance(daily, dict) or not daily:
        raise ValueError("daily_by_utc_date empty in fills cache")
    items: list[dict[str, Any]] = []
    dates = sorted(daily.keys())
    for rep in range(max(1, repeat)):
        for utc_date in dates:
            row = daily.get(utc_date)
            if not isinstance(row, dict):
                continue
            payload = {"utc_date": utc_date, **row}
            prompt = FILLS_DAILY_TEMPLATE.format(
                payload=json.dumps(payload, ensure_ascii=False, indent=2)
            )
            items.append(
                {
                    "lane": "btrack_fills_daily",
                    "utc_date": utc_date,
                    "repeat": rep + 1,
                    "prompt_profile": "btrack_fills_daily",
                    "prompt": prompt + f"\n[burn-meta] lane=btrack_fills_daily date={utc_date} rep={rep+1}",
                }
            )
    return items


def build_profile_prompts(profile: str, count: int) -> list[dict[str, Any]]:
    seeds = _import_profile_seeds(profile)
    items: list[dict[str, Any]] = []
    i = 0
    while len(items) < count:
        base = seeds[i % len(seeds)]
        idx = len(items) + 1
        prompt = f"{base}\n\n[burn-meta] profile={profile} index={idx}/{count} tier=B research_only"
        items.append(
            {
                "lane": profile,
                "prompt_profile": profile,
                "index": idx,
                "prompt": prompt,
            }
        )
        i += 1
    return items


def build_bundle(
    lanes: dict[str, int],
    fills_cache: Path,
    fills_repeat: int,
) -> dict[str, Any]:
    bundle_lanes: dict[str, Any] = {}
    total = 0
    if lanes.get("btrack_fills_daily", 0) > 0 or "btrack_fills_daily" in lanes:
        fills_items = build_btrack_fills_daily_prompts(fills_cache, repeat=fills_repeat)
        cap = lanes.get("btrack_fills_daily") or len(fills_items)
        fills_items = fills_items[:cap]
        bundle_lanes["btrack_fills_daily"] = fills_items
        total += len(fills_items)
    for profile in ("asset_rag", "cross_lens", "wellness_hypo", "quota_stress"):
        n = lanes.get(profile, 0)
        if n > 0:
            items = build_profile_prompts(profile, n)
            bundle_lanes[profile] = items
            total += len(items)
    return {
        "schema": "mkm_productive_burn_bundle_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "track_wall": "btrack_research_only",
        "billing_account_id": "010B19-239742-DAF438",
        "allowed_projects": [
            "gen-lang-client-0846393371",
            "artful-athlete-490017-k3",
        ],
        "total_prompts": total,
        "lanes": bundle_lanes,
        "fills_cache_source": str(fills_cache.relative_to(ROOT)).replace("\\", "/"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--lane",
        choices=[
            "btrack_fills_daily",
            "asset_rag",
            "cross_lens",
            "wellness_hypo",
            "quota_stress",
            "all_productive",
        ],
        default="all_productive",
    )
    ap.add_argument("--fills-cache", type=Path, default=FILLS_CACHE)
    ap.add_argument("--fills-repeat", type=int, default=3, help="Repeat daily rows to reach call target")
    ap.add_argument("--asset-rag-calls", type=int, default=600)
    ap.add_argument("--cross-lens-calls", type=int, default=400)
    ap.add_argument("--fills-calls", type=int, default=200)
    ap.add_argument("--quota-stress-calls", type=int, default=0)
    ap.add_argument("--export-bundle", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    lane_map: dict[str, int] = {}
    if args.lane == "all_productive":
        lane_map = {
            "btrack_fills_daily": args.fills_calls,
            "asset_rag": args.asset_rag_calls,
            "cross_lens": args.cross_lens_calls,
            "quota_stress": args.quota_stress_calls,
        }
    elif args.lane == "btrack_fills_daily":
        lane_map = {"btrack_fills_daily": args.fills_calls}
    else:
        lane_map = {args.lane: args.asset_rag_calls if args.lane == "asset_rag" else args.cross_lens_calls}

    bundle = build_bundle(lane_map, args.fills_cache, args.fills_repeat)

    if args.stdout_only:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        return 0

    args.export_bundle.parent.mkdir(parents=True, exist_ok=True)
    args.export_bundle.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.export_bundle),
                "total_prompts": bundle["total_prompts"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
