from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    root = Path("C:/workspace")
    rel_targets = [
        "docs/final/artifacts/mkm_trackc_external_onepager_latest.md",
        "docs/final/artifacts/mkm_trackc_api_spec_package_latest.md",
        "docs/final/artifacts/mkm_trackc_client_handoff_package_latest.md",
    ]

    files: List[Dict[str, object]] = []
    missing: List[str] = []
    for rel in rel_targets:
        p = (root / rel).resolve()
        if not p.exists():
            missing.append(rel)
            continue
        files.append(
            {
                "path": rel,
                "size_bytes": p.stat().st_size,
                "sha256": _sha256(p),
                "last_modified_utc": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )

    status = "FROZEN" if not missing else "PARTIAL"
    payload = {
        "schema": "mkm_trackc_delivery_freeze_log_v1",
        "generated_at_utc": _utc_now(),
        "status": status,
        "missing_files": missing,
        "frozen_files": files,
    }

    out_json = root / "docs/final/artifacts/mkm_trackc_delivery_freeze_log_latest.json"
    out_md = root / "docs/final/artifacts/mkm_trackc_delivery_freeze_log_latest.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# MKM Track C Delivery Freeze Log",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{status}`",
        f"- file_count: `{len(files)}`",
    ]
    if missing:
        lines.append("- missing_files:")
        for m in missing:
            lines.append(f"  - `{m}`")
    lines.append("")
    lines.append("## Frozen Files")
    for item in files:
        lines.append(f"- `{item['path']}`")
        lines.append(f"  - size_bytes: `{item['size_bytes']}`")
        lines.append(f"  - sha256: `{item['sha256']}`")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"freeze log json written: {out_json}")
    print(f"freeze log md written: {out_md}")
    print(f"status={status}")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
