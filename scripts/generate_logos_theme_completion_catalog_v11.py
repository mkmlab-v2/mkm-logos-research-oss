#!/usr/bin/env python3
"""Generate logos_theme_completion_catalog_v11.json — cycle v11 narratives (Track B)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from generate_logos_theme_completion_catalog_v3 import META, title

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "docs/research/logos_metaphor_db_v1"
OUT = ROOT / "scripts/data/logos_theme_completion_catalog_v11.json"
CANDIDATES_PATH = ROOT / "scripts/data/logos_theme_completion_candidates_v11_v1.json"

META_V11 = {
    **META,
    "lot_wife_pillar_salt": ("롯의 아내 소금 기둥", "창세기 19:26", "뒤를 돌아본 자가", "롤백 금지·후행 관측 비유"),
    "tree_of_life_monthly_fruit": ("생명나무 열매", "요한계시록 22:2", "그 잎사귀는 만민을", "월간 배치·릴리스 비유"),
}


def _load_candidates() -> list[str]:
    if CANDIDATES_PATH.is_file():
        return [str(s) for s in json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))]
    raise FileNotFoundError(CANDIDATES_PATH)


def _on_disk_slugs() -> set[str]:
    slugs: set[str] = set()
    for path in DB.glob("theme_*.json"):
        m = re.match(r"^theme_\d+_(.+)\.json$", path.name)
        if m:
            slugs.add(m.group(1))
    for v in range(1, 12):
        p = ROOT / f"scripts/data/logos_theme_completion_catalog_v{v}.json"
        if p.is_file():
            for c in json.loads(p.read_text(encoding="utf-8")):
                slugs.add(c["slug"])
    return slugs


def main() -> int:
    on_disk = _on_disk_slugs()
    slugs = [c for c in _load_candidates() if c not in on_disk and not c.endswith("_alt")]
    meta = META_V11
    out: list[dict] = []
    for slug in slugs:
        if slug in meta:
            ko, ref, txt, core = meta[slug]
            theme = f"{ko} ({title(slug)})"
            note = f"{core}이며 [HYPO] Track A·실매매 단정 아님."
        else:
            theme = f"{title(slug)} (Track B)"
            ref, txt = "시편 119:105", "주의 말씀은 내 발에 등이요"
            note = f"{title(slug)} 은유는 B-track ops·거버넌스 비유이며 [HYPO] 단정 아님."
        out.append(
            {"slug": slug, "theme": theme, "anchor_ref": ref, "anchor_text": txt, "note": note}
        )

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} -> {OUT}")
    if out:
        print(f"range {out[0]['slug']} .. {out[-1]['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
