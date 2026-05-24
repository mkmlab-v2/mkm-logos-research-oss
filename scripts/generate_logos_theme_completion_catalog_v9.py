#!/usr/bin/env python3
"""Generate logos_theme_completion_catalog_v9.json — cycle v9 narratives (Track B)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from generate_logos_theme_completion_catalog_v3 import META, title

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "docs/research/logos_metaphor_db_v1"
OUT = ROOT / "scripts/data/logos_theme_completion_catalog_v9.json"
CANDIDATES_PATH = ROOT / "scripts/data/logos_theme_completion_candidates_v9_v1.json"

META_V9 = {
    **META,
    "revelation_seven_lampstands": ("일곱 촛대", "요한계시록 1:20", "일곱 촛대는 일곱 교회를", "테넌트 샤드·램프스탠드 비유"),
    "144000_sealed": ("14만4천 인침", "요한계시록 7:4", "이마에 인을 받은", "허용 목록·쿼터 캡 비유"),
    "gethsemane_watch_sleep": ("겟세마네 잠", "마태복음 26:40", "한 시간 동안 잠을 자지 못하셨나", "온콜 졸림·워치 실패 비유"),
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
    for v in range(1, 10):
        p = ROOT / f"scripts/data/logos_theme_completion_catalog_v{v}.json"
        if p.is_file():
            for c in json.loads(p.read_text(encoding="utf-8")):
                slugs.add(c["slug"])
    return slugs


def main() -> int:
    on_disk = _on_disk_slugs()
    slugs = [c for c in _load_candidates() if c not in on_disk and not c.endswith("_alt")]
    meta = META_V9
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
