"""
Export clinic constitution survey pack for mkmlife public + legacy bridge copy.

Writes:
  projects/mkm/mkm-life/public/data/clinic_constitution_survey_pack_v1.json
  projects/mkm/mkm-life/public/data/clinic_constitution_survey_legacy_bridge_v1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
BANK_REL = Path("docs/final/artifacts/clinic_constitution_survey_item_bank_v1.json")
BRIDGE_REL = Path("docs/final/artifacts/clinic_constitution_survey_legacy_bridge_v1.json")
MAI_COPY_REL = Path("docs/final/artifacts/gtm_mai_copy_bundles_v1.json")
MKMLIFE_DATA = Path("projects/mkm/mkm-life/public/data")

CORE_ITEM_IDS = ["ch02", "dg02", "ac02", "ch01", "dg01"]

DISCLAIMER_KO = (
    "[HYPO] 참고용 체질 가설입니다. 한의사 확정 진단·처방이 아니며, "
    "증상 악화 시 의료기관 상담을 우선하세요."
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export survey pack to mkmlife public/data")
    p.add_argument("--root", type=Path, default=_ROOT)
    args = p.parse_args(argv)
    root = args.root

    bank = json.loads((root / BANK_REL).read_text(encoding="utf-8"))
    public = {
        "schema": "clinic_constitution_survey_pack_public_v1",
        "version": "1.0.0",
        "pack_id": bank.get("pack_id"),
        "lane": bank.get("lane"),
        "hypothesis_tier": "B",
        "research_only": True,
        "scale_default": bank.get("scale_default"),
        "core_item_ids": CORE_ITEM_IDS,
        "disclaimer_ko": DISCLAIMER_KO,
        "items": [
            {
                "item_id": it["item_id"],
                "prompt_ko": it["prompt_ko"],
                "axis": it["axis"],
                "core_required": it["item_id"] in CORE_ITEM_IDS,
            }
            for it in bank.get("items", [])
            if isinstance(it, dict)
        ],
        "policy_ref": "docs/final/artifacts/clinic_constitution_dual_lane_policy_v1.json",
        "score_script": "scripts/score_clinic_constitution_survey_v1.py",
        "score_api_path": "/api/v1/constitution/survey/score",
        "mai_product_name": "MAI",
        "mai_copy_bundles_ref": "gtm_mai_copy_bundles_v1.json",
    }

    out_dir = root / MKMLIFE_DATA
    out_dir.mkdir(parents=True, exist_ok=True)
    pack_path = out_dir / "clinic_constitution_survey_pack_v1.json"
    pack_path.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    bridge_src = root / BRIDGE_REL
    bridge_dst = out_dir / "clinic_constitution_survey_legacy_bridge_v1.json"
    bridge_dst.write_text(bridge_src.read_text(encoding="utf-8"), encoding="utf-8")

    mai_dst = out_dir / "gtm_mai_copy_bundles_v1.json"
    mai_dst.write_text((root / MAI_COPY_REL).read_text(encoding="utf-8"), encoding="utf-8")

    print(
        json.dumps(
            {"pack": str(pack_path), "bridge": str(bridge_dst), "mai_copy": str(mai_dst)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
