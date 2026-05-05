#!/usr/bin/env python3
"""Update Global Atom corpus profile approval log heartbeat."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_log = root / "docs" / "final" / "artifacts" / "GLOBAL_ATOM_CORPUS_PROFILE_CHANGE_APPROVAL_LOG_LATEST.md"
    default_claim = root / "docs" / "final" / "artifacts" / "global_atom_claim_lock_registry_latest.json"

    ap = argparse.ArgumentParser(description="Refresh approval log current status timestamp.")
    ap.add_argument("--log-md", default=str(default_log))
    ap.add_argument("--claim-lock-json", default=str(default_claim))
    args = ap.parse_args()

    now = _now_utc()
    claim_doc = _load_json(Path(args.claim_lock_json))
    current_profile = claim_doc.get("corpus_profile_id", "unknown")
    log_path = Path(args.log_md)
    lines = log_path.read_text(encoding="utf-8").splitlines()
    out = []
    for ln in lines:
        if ln.startswith("- `current_corpus_profile_id`:"):
            out.append(f"- `current_corpus_profile_id`: `{current_profile}`")
        elif ln.startswith("- `last_reviewed_at_utc`:"):
            out.append(f"- `last_reviewed_at_utc`: `{now}`")
        elif ln.startswith("- `review_note`:"):
            out.append("- `review_note`: `No profile change requested; automated daily heartbeat updated.`")
        else:
            out.append(ln)
    log_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": "global_atom_profile_approval_log_update_v1",
                "updated_at_utc": now,
                "log_md": str(log_path),
                "current_corpus_profile_id": current_profile,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
