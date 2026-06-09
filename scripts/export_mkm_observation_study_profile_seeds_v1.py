#!/usr/bin/env python3
"""Export consumer-safe study profile seeds for L2 observation API (CF ASSETS fallback)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / "projects/mkm/mkm-life/.mkm-study-store.json"
DEFAULT_OUT = ROOT / "projects/mkm/mkm-life/public/data/mkm_observation_study_profile_seeds_v1.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store-json", type=Path, default=DEFAULT_STORE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.store_json.is_file():
        print(f"missing store: {args.store_json}")
        return 2
    store = json.loads(args.store_json.read_text(encoding="utf-8-sig"))
    profiles = []
    seen: set[str] = set()
    for row in store.get("profiles") or []:
        if not isinstance(row, dict):
            continue
        sid = str(row.get("studentId") or "").strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        profiles.append(
            {
                "student_id": sid,
                "a_code_type": row.get("aCodeType"),
                "a_code_label_ko": row.get("aCodeLabel"),
                "onboarding_stage": row.get("onboardingStage"),
                "grade": row.get("grade"),
            }
        )
    out = {
        "schema": "mkm_observation_study_profile_seeds_v1",
        "lane": "research_only",
        "hypothesis_tag": "[HYPO]",
        "profiles": profiles,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {args.out_json.relative_to(ROOT)} profiles={len(profiles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
