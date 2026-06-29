#!/usr/bin/env python3
"""Build Saving the News counsel ZIP from export manifest."""
from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/saving_the_news_counsel_export_manifest_v1_latest.json"
DEFAULT_ZIP = ROOT / "docs/final/artifacts/saving_the_news_counsel_export_pack_v1.zip"
DEFAULT_META = ROOT / "docs/final/artifacts/saving_the_news_counsel_zip_pack_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_zip(*, zip_path: Path) -> dict[str, Any]:
    if not MANIFEST.is_file():
        raise FileNotFoundError(f"missing manifest: {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    included: list[str] = []
    missing: list[str] = []
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for row in manifest.get("files") or []:
            if not isinstance(row, dict):
                continue
            rel = str(row.get("path") or "")
            src = ROOT / rel
            if not src.is_file():
                missing.append(rel)
                continue
            zf.write(src, rel.replace("\\", "/"))
            included.append(rel)
        zf.writestr(
            "00_README_COUNSEL_INDEX.txt",
            (
                "MKM Track C — Saving the News counsel review pack\n"
                f"generated_at_utc: {_utc_now()}\n"
                f"file_count: {len(included)}\n"
                "lane: research_only · ready_for_external_send: false\n"
                "NOT legal sign-off. INTERNAL review until counsel reference recorded.\n"
                "Live surfaces (reference only): mkmlife.com/news-deck · "
                "jemaai.cloud/public_showroom_saving_the_news_matrix_v1.html\n"
            ),
        )
        if MANIFEST.is_file():
            zf.write(MANIFEST, "docs/final/artifacts/saving_the_news_counsel_export_manifest_v1_latest.json")
    return {
        "schema": "saving_the_news_counsel_zip_pack_v1",
        "generated_at_utc": _utc_now(),
        "zip_path": zip_path.relative_to(ROOT).as_posix(),
        "included_count": len(included),
        "missing_count": len(missing),
        "included": included,
        "missing": missing,
        "ok": len(missing) == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip-out", type=Path, default=DEFAULT_ZIP)
    ap.add_argument("--meta-json", type=Path, default=DEFAULT_META)
    args = ap.parse_args()
    meta = build_zip(zip_path=args.zip_out)
    args.meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": meta["ok"], "zip": str(args.zip_out), "included": meta["included_count"]}, ensure_ascii=False))
    return 0 if meta["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
