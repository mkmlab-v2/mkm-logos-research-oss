#!/usr/bin/env python3
"""Copy K-Startup 창업패키지 AI downloads into repo attachments folder."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
OUT = ROOT / "reports/kstartup_startup_package_ai_attachments"
PORTAL = (
    "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
    "?pbancClssCd=PBC010&schM=view&pbancSn=177670"
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copied: list[dict] = []
    if not DOWNLOADS.is_dir():
        print(f"Downloads missing: {DOWNLOADS}")
        return 1
    for f in DOWNLOADS.iterdir():
        if not f.is_file():
            continue
        n = f.name
        if not (
            "창업패키지" in n
            and "AI" in n
            or "창업도약" in n
            or ("초기창업패키지" in n and "AI" in n)
        ):
            continue
        dest = OUT / f.name
        shutil.copy2(f, dest)
        track = "doyak" if "도약" in n else ("chogi" if "초기" in n else "common")
        copied.append(
            {
                "name": f.name,
                "rel": f"reports/kstartup_startup_package_ai_attachments/{f.name}",
                "bytes": f.stat().st_size,
                "track": track,
            }
        )
    doyak = next(
        (c for c in copied if c["track"] == "doyak" and "별첨" in c["name"] and c["name"].endswith(".docx")),
        None,
    )
    notice = next((c for c in copied if "공고문" in c["name"]), None)
    manifest = {
        "schema": "kstartup_startup_package_ai_attachments_manifest_v1",
        "generated_at_utc": _utc(),
        "portal_detail_url": PORTAL,
        "pbanc_sn": "177670",
        "track_recommended": "doyak",
        "files": copied,
        "paths": {
            "doyak_plan_docx": doyak["rel"] if doyak else None,
            "notice_pdf": notice["rel"] if notice else None,
        },
    }
    (OUT / "manifest_latest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"copied={len(copied)} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
