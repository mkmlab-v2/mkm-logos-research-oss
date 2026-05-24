#!/usr/bin/env python3
"""Build full atom_id diff between 41775 and 41658 master codebook exports (evidence package A)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_775 = PILOT / "master_codebook_lexicon_v1_41775_rows_latest.json"
DEFAULT_658 = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"


def _resolve_codebook_41775(path: Path) -> Path:
    if path.is_file():
        return path
    archived = sorted(PILOT.glob("master_codebook_lexicon_v1_41775_rows_archived_*.json"), reverse=True)
    return archived[0] if archived else path
DEFAULT_OUT = PILOT / "master_codebook_41775_vs_41658_atom_diff_v1.json"
_ATOM_ID_RE = re.compile(r'"atom_id":"([^"]+)"')


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _header_meta(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        head = f.read(4096)
    row_m = re.search(r'"row_count":(\d+)', head)
    gen_m = re.search(r'"generated_at_utc":"([^"]+)"', head)
    atoms_sha = None
    atoms_m = re.search(r'"atoms":\{"path":"[^"]*","sha256":"([a-f0-9]{64})"', head)
    if atoms_m:
        atoms_sha = atoms_m.group(1)
    return {
        "path": str(path.resolve()),
        "row_count": int(row_m.group(1)) if row_m else None,
        "generated_at_utc": gen_m.group(1) if gen_m else None,
        "inputs_atoms_sha256": atoms_sha,
        "file_sha256": _sha256_file(path),
    }


def _atom_ids(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(_ATOM_ID_RE.findall(text))


def _lang_bucket(atom_id: str) -> str:
    return atom_id.split("::", 1)[0] if "::" in atom_id else "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build master codebook 41775 vs 41658 atom diff v1")
    ap.add_argument("--codebook-41775", type=Path, default=DEFAULT_775)
    ap.add_argument("--codebook-41658", type=Path, default=DEFAULT_658)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    p775 = _resolve_codebook_41775(
        args.codebook_41775 if args.codebook_41775.is_absolute() else ROOT / args.codebook_41775
    )
    p658 = args.codebook_41658 if args.codebook_41658.is_absolute() else ROOT / args.codebook_41658
    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json

    for p in (p775, p658):
        if not p.is_file():
            print(f"ERROR: missing {p}")
            return 2

    ids775 = _atom_ids(p775)
    ids658 = _atom_ids(p658)
    only775 = sorted(ids775 - ids658)
    only658 = sorted(ids658 - ids775)

    by_lang: dict[str, dict[str, int]] = {}
    for prefix in ("greek::", "hebrew::", "other::"):
        g775 = {x for x in ids775 if x.startswith(prefix)}
        g658 = {x for x in ids658 if x.startswith(prefix)}
        by_lang[prefix.rstrip(":")] = {
            "count_41775": len(g775),
            "count_41658": len(g658),
            "only_in_41775": len(g775 - g658),
            "only_in_41658": len(g658 - g775),
        }

    gh775 = {x for x in ids775 if x.startswith(("greek::", "hebrew::"))}
    gh658 = {x for x in ids658 if x.startswith(("greek::", "hebrew::"))}
    greek_hebrew_parity = gh775 == gh658

    gh_only775 = [x for x in only775 if x.startswith(("greek::", "hebrew::"))]
    gh_only658 = [x for x in only658 if x.startswith(("greek::", "hebrew::"))]

    payload: dict[str, Any] = {
        "schema": "master_codebook_41775_vs_41658_atom_diff_v1",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "greek_hebrew_parity": greek_hebrew_parity,
        "greek_hebrew_symmetric_delta": len(gh775 ^ gh658),
        "greek_hebrew_only_in_41775": gh_only775,
        "greek_hebrew_only_in_41658": gh_only658,
        "ids_41775": len(ids775),
        "ids_41658": len(ids658),
        "net_row_delta": len(ids775) - len(ids658),
        "only_in_41775_count": len(only775),
        "only_in_41658_count": len(only658),
        "only_in_41775_lang": dict(Counter(_lang_bucket(x) for x in only775)),
        "only_in_41658_lang": dict(Counter(_lang_bucket(x) for x in only658)),
        "by_lang_prefix": by_lang,
        "only_in_41775": only775,
        "only_in_41658": only658,
        "codebook_41775_meta": _header_meta(p775),
        "codebook_41658_meta": _header_meta(p658),
        "interpretation": {
            "row_gap_cause": "other_bucket_token_drift_between_exports",
            "nt_canon_15_verse_gap": "separate_axis_logos_gap_mt_only_residual_classify_v1_latest",
            "fail_comp_004": "do_not_edit_MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_without_human_signoff",
        },
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: master codebook atom diff v1")
    print(f"out={out}")
    print(f"greek_hebrew_parity={greek_hebrew_parity}")
    print(f"only_in_41775={len(only775)} only_in_41658={len(only658)} net={len(ids775) - len(ids658)}")
    return 0 if greek_hebrew_parity and not gh_only775 and not gh_only658 else 1


if __name__ == "__main__":
    raise SystemExit(main())
