#!/usr/bin/env python3
"""Generate logos_theme_completion_catalog_v4.json — remaining v3 CANDIDATES (Track B)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from generate_logos_theme_completion_catalog_v3 import CANDIDATES, META, title

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "docs/research/logos_metaphor_db_v1"
OUT = ROOT / "scripts/data/logos_theme_completion_catalog_v4.json"


def _on_disk_slugs() -> set[str]:
    slugs: set[str] = set()
    for path in DB.glob("theme_*.json"):
        m = re.match(r"^theme_\d+_(.+)\.json$", path.name)
        if m:
            slugs.add(m.group(1))
    for v in ("v1", "v2", "v3", "v4"):
        p = ROOT / f"scripts/data/logos_theme_completion_catalog_{v}.json"
        if p.is_file():
            for c in json.loads(p.read_text(encoding="utf-8")):
                slugs.add(c["slug"])
    return slugs


def main() -> int:
    on_disk = _on_disk_slugs()
    slugs = [c for c in CANDIDATES if c not in on_disk and not c.endswith("_alt")]
    out: list[dict] = []
    for slug in slugs:
        if slug in META:
            ko, ref, txt, core = META[slug]
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
