#!/usr/bin/env python3
"""Validate trading_human_execution_approval_v1 JSON (schema + optional SHA-256 + GO expiry).

No network, no orders. Intended gate before any live trading script consumes a receipt.

Exit codes:
  0 OK
  1 JSON Schema validation failed
  2 proposal_body_sha256 mismatch (proposal file was read)
  3 GO receipt expired (valid_until_utc in the past)
  4 proposal file missing or unreadable when verification was required
  5 GO without verifiable proposal file path
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "final" / "artifacts" / "schemas" / "trading_human_execution_approval_v1.schema.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_z(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _proposal_path(
    approval: Dict[str, Any], workspace: Path, proposal_file: Optional[Path]
) -> Optional[Path]:
    if proposal_file is not None:
        p = proposal_file if proposal_file.is_absolute() else (workspace / proposal_file)
        return p.resolve()
    ref = approval.get("proposal_ref")
    if isinstance(ref, dict):
        ap = ref.get("artifact_path")
        if isinstance(ap, str) and ap.strip():
            p = workspace / ap.strip()
            return p.resolve()
    return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_schema(doc: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:
        return False, f"jsonschema required: {e}"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errs = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if errs:
        msg = "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:16])
        return False, msg
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--approval",
        type=Path,
        required=True,
        help="Path to trading_human_execution_approval_v1 JSON.",
    )
    ap.add_argument(
        "--workspace-root",
        type=Path,
        default=ROOT,
        help="Workspace root for resolving proposal_ref.artifact_path (default: repo root).",
    )
    ap.add_argument(
        "--proposal-file",
        type=Path,
        default=None,
        help="Override proposal file path for SHA-256 verification.",
    )
    ap.add_argument(
        "--skip-expiry",
        action="store_true",
        help="Do not treat past valid_until_utc as failure (testing only).",
    )
    args = ap.parse_args()

    workspace = args.workspace_root.resolve()
    approval_path = args.approval.resolve()
    if not SCHEMA_PATH.is_file():
        print(f"MISSING_SCHEMA: {SCHEMA_PATH}", file=sys.stderr)
        return 1
    try:
        doc = _load_json(approval_path)
    except OSError as e:
        print(f"READ_ERROR: {approval_path}: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"JSON_ERROR: {e}", file=sys.stderr)
        return 1

    ok, err = _validate_schema(doc)
    if not ok:
        print(f"SCHEMA_ERROR: {err}", file=sys.stderr)
        return 1

    decision = str(doc.get("decision") or "")
    valid_until = _parse_iso_z(str(doc["valid_until_utc"]))
    if decision == "GO" and not args.skip_expiry:
        if _utc_now() > valid_until.replace(tzinfo=timezone.utc):
            print("EXPIRED_GO: valid_until_utc is in the past.", file=sys.stderr)
            return 3

    expected = str(doc.get("proposal_body_sha256") or "").lower()
    ppath = _proposal_path(doc, workspace, args.proposal_file)
    if decision == "GO":
        if ppath is None:
            print(
                "MISSING_PROPOSAL_PATH: GO requires proposal_ref.artifact_path or --proposal-file.",
                file=sys.stderr,
            )
            return 5
        if not ppath.is_file():
            print(f"MISSING_PROPOSAL_FILE: {ppath}", file=sys.stderr)
            return 4
        got = _sha256_file(ppath).lower()
        if got != expected:
            print(
                f"HASH_MISMATCH: file={ppath}\nexpected={expected}\nactual={got}",
                file=sys.stderr,
            )
            return 2
    else:
        if ppath is not None and ppath.is_file():
            got = _sha256_file(ppath).lower()
            if got != expected:
                print(
                    f"HASH_MISMATCH: file={ppath}\nexpected={expected}\nactual={got}",
                    file=sys.stderr,
                )
                return 2

    print("OK: trading_human_execution_approval_v1 validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
