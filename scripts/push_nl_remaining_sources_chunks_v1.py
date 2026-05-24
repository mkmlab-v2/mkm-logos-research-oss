#!/usr/bin/env python3
"""Split large NL uploads into ~40k chunks for MCP add_source."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "constitution" / "btrack_pilot"
CHUNK = 40_000

FILES = [
    ("CENTRAL", "nl_upload_central_v1.txt"),
    ("ACTIVE_REPORT", "nl_upload_active_report_v1.txt"),
]


def main() -> int:
    manifest = []
    for label, fname in FILES:
        text = (OUT / fname).read_text(encoding="utf-8")
        parts = [text[i : i + CHUNK] for i in range(0, len(text), CHUNK)]
        for i, part in enumerate(parts):
            out_name = f"nl_chunk_{label.lower()}_{i}.txt"
            (OUT / out_name).write_text(part, encoding="utf-8")
            manifest.append({"label": label, "part": i, "file": out_name, "chars": len(part)})
    (OUT / "nl_chunk_manifest_v1.json").write_text(
        __import__("json").dumps(manifest, indent=2), encoding="utf-8"
    )
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
