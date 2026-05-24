#!/usr/bin/env python3
"""Generate logos_theme_completion_catalog_v10.json — cycle v10 narratives (Track B)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from generate_logos_theme_completion_catalog_v3 import META, title

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "docs/research/logos_metaphor_db_v1"
OUT = ROOT / "scripts/data/logos_theme_completion_catalog_v10.json"
CANDIDATES_PATH = ROOT / "scripts/data/logos_theme_completion_candidates_v10_v1.json"

META_V10 = {
    **META,
    "revelation_lamb_throne_center": ("어린 양 보좌 중심", "요한계시록 5:6", "보좌 가운데 어린 양", "중앙 코디네이터·SSOT 비유"),
    "four_horsemen_apocalypse": ("네 기수", "요한계시록 6:2-8", "네 기수가 나오니", "장애 시나리오·카탈로그 비유"),
    "new_jerusalem_no_temple": ("새 예루살렘 성전 없음", "요한계시록 21:22", "성전을 보이지 아니하니", "단일 게이트웨이·중복 제거 비유"),
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
    for v in range(1, 11):
        p = ROOT / f"scripts/data/logos_theme_completion_catalog_v{v}.json"
        if p.is_file():
            for c in json.loads(p.read_text(encoding="utf-8")):
                slugs.add(c["slug"])
    return slugs


def main() -> int:
    on_disk = _on_disk_slugs()
    slugs = [c for c in _load_candidates() if c not in on_disk and not c.endswith("_alt")]
    meta = META_V10
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
