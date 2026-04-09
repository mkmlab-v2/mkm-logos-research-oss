"""Track B artifact alias pointers for deprecated paths (research-only)."""
from __future__ import annotations

import json
from pathlib import Path

ALIAS_SCHEMA = "trackb_artifact_alias_v1"


def write_alias(*, legacy_path: Path, canonical_relative: str) -> None:
    rel = canonical_relative.replace("\\", "/")
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(
        json.dumps(
            {
                "schema": ALIAS_SCHEMA,
                "canonical_relative": rel,
                "deprecated_filename": legacy_path.name,
                "note": "Prefer canonical artifact; alias retained for backward compatibility.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def resolve_alias_doc(root: Path, path: Path) -> tuple[dict, Path]:
    """Load JSON at path; if alias, load canonical. Returns (doc, resolved_path)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") == ALIAS_SCHEMA:
        can = root / doc["canonical_relative"]
        return json.loads(can.read_text(encoding="utf-8")), can
    return doc, path
