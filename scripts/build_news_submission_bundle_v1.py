#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DIR = ART / "news_submission_bundle"

REQUIRED_FILES = [
    ART / "news_claim_pack_latest.json",
    ART / "news_benchmark_readiness_latest.json",
    ART / "news_third_party_repro_bundle_latest.json",
    ART / "news_claim_pack_latest.md",
    ART / "news_benchmark_readiness_latest.md",
    ART / "NEWS_BENCHMARK_PRESS_ONEPAGER_FINAL_V1.md",
    ART / "NEWS_BENCHMARK_PRESS_ONEPAGER_FINAL_KO_V1.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksums(entries: Iterable[tuple[Path, str]], out_path: Path) -> None:
    lines = [f"{digest}  {path.as_posix()}" for path, digest in entries]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build news submission bundle zip + checksum manifest.")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if Path(args.out_dir).is_absolute() else (ROOT / args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    missing = [str(p) for p in REQUIRED_FILES if not p.exists()]
    if missing:
        raise SystemExit("Missing required files:\n- " + "\n- ".join(missing))

    stamp = utc_now()
    zip_path = out_dir / f"news_submission_bundle_{stamp}.zip"
    checksums_path = out_dir / f"news_submission_bundle_{stamp}_sha256.txt"
    index_path = out_dir / "news_submission_bundle_latest.json"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src in REQUIRED_FILES:
            arc = src.relative_to(ROOT).as_posix()
            zf.write(src, arcname=arc)

    checksum_entries = [(p.relative_to(ROOT), sha256(p)) for p in REQUIRED_FILES]
    checksum_entries.append((zip_path.relative_to(ROOT), sha256(zip_path)))
    write_checksums(checksum_entries, checksums_path)

    index = {
        "schema": "news_submission_bundle_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bundle_zip": str(zip_path.relative_to(ROOT)).replace("\\", "/"),
        "checksums_txt": str(checksums_path.relative_to(ROOT)).replace("\\", "/"),
        "included_files": [str(p.relative_to(ROOT)).replace("\\", "/") for p in REQUIRED_FILES],
    }
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(str(zip_path))
    print(str(checksums_path))
    print(str(index_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

