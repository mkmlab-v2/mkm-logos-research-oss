#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DROP = ROOT / "reports" / "news_repro" / "latest"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Fill manifest/log sha256 fields in independent_result_digest.json")
    ap.add_argument("--dropzone", default=str(DEFAULT_DROP))
    args = ap.parse_args()

    drop = Path(args.dropzone) if Path(args.dropzone).is_absolute() else (ROOT / args.dropzone)
    manifest = drop / "external_runner_manifest.json"
    raw_log = drop / "raw_benchmark.log"
    digest_path = drop / "independent_result_digest.json"

    for req in (manifest, raw_log, digest_path):
        if not req.exists():
            raise SystemExit(f"Missing required file: {req}")

    digest = _read_json(digest_path)
    digest.setdefault("artifacts", {})
    digest["artifacts"]["manifest_path"] = str(manifest.resolve())
    digest["artifacts"]["raw_log_path"] = str(raw_log.resolve())
    digest["artifacts"]["manifest_sha256"] = _sha256(manifest)
    digest["artifacts"]["raw_log_sha256"] = _sha256(raw_log)

    digest_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(digest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

