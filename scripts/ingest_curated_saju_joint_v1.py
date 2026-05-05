#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ingest human-curated rows into ``sasang_saju_joint_benchmark_v1.jsonl`` (NON-INVENTION gate).

**Standard input:** ``data/myeongni/curated_saju_joint_v1.jsonl`` — one JSON object per line.

**Provenance gate:** at least one of ``provenance_url``, ``source_url`` (alias), or ``source_citation``
must be non-empty after strip. Otherwise the row is logged as ``SKIP_UNVERIFIED`` and never sent to
the birth engine (no DOB invention).

**Birth fields (required for promoted rows):**

- ``birth_instant_utc`` or ``dob_utc`` — ISO8601 ending in ``Z``
- ``iana_tz`` — IANA zone (default ``Etc/UTC`` if absent; recorded in output)
- ``is_male`` — bool, or ``sex`` in ``m``/``male``/``f``/``female``

Optional: ``person_id``, ``name`` / ``display_name``, ``sasang_label_ko``, ``sasang_label_en``,
``note``, ``literature_catalog_pmids`` (list), ``provenance`` (free tag e.g. ``verified_history_v1``),
``ingest_at_utc`` (ISO Z; staleness report vs hit-rate artifact).

Output rows use schema ``sasang_saju_joint_benchmark_row_v1`` (same contract as
``promote_joint_curated_csv_v1.py``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "myeongni" / "curated_saju_joint_v1.jsonl"
DEFAULT_TARGET = ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_v1.jsonl"

_ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def _has_verified_provenance(obj: dict[str, Any]) -> bool:
    url = str(obj.get("provenance_url") or obj.get("source_url") or "").strip()
    cite = str(obj.get("source_citation") or "").strip()
    return bool(url or cite)


def _parse_bool_male(obj: dict[str, Any]) -> bool | None:
    if "is_male" in obj and obj["is_male"] is not None:
        v = obj["is_male"]
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("1", "y", "yes", "true", "m", "male"):
            return True
        if s in ("0", "n", "no", "false", "f", "female"):
            return False
        return None
    s = str(obj.get("sex") or "").strip().lower()
    if s in ("m", "male", "1", "y", "yes"):
        return True
    if s in ("f", "female", "0", "n", "no"):
        return False
    return None


def _birth_instant(obj: dict[str, Any]) -> str:
    return str(obj.get("birth_instant_utc") or obj.get("dob_utc") or "").strip()


def _display_name(obj: dict[str, Any], *, line_no: int, fallback_id: str) -> str:
    for k in ("display_name", "name"):
        v = str(obj.get(k) or "").strip()
        if v:
            return v[:240]
    return fallback_id


def _person_id(obj: dict[str, Any], *, line_no: int, payload_digest: str) -> str:
    pid = str(obj.get("person_id") or "").strip()
    if pid:
        return pid[:180]
    base = _display_name(obj, line_no=line_no, fallback_id=f"line_{line_no}")
    slug = re.sub(r"[^a-zA-Z0-9가-힣_-]+", "_", base)[:80].strip("_") or "anon"
    return f"curated_jsonl_{slug}_{line_no}_{payload_digest[:8]}"


def _run_birth_cli(birth_instant_utc: str, iana_tz: str, is_male: bool) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_saju_global_birth_v1.py"),
        "--utc-instant",
        birth_instant_utc,
        "--iana-tz",
        iana_tz,
        "--compact",
    ]
    if is_male:
        cmd.append("--is-male")
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout or "run_saju_global_birth_v1 failed")
    line = (p.stdout or "").strip()
    if line.startswith("\ufeff"):
        line = line[1:]
    return json.loads(line)


def _existing_person_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        pid = str(r.get("person_id") or "").strip()
        if pid:
            out.add(pid)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--target-jsonl", type=Path, default=DEFAULT_TARGET)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        print(
            json.dumps(
                {
                    "ok": True,
                    "skipped": "missing_input_file",
                    "path": str(args.input_jsonl),
                    "hint": "create empty file or add curated rows",
                },
                ensure_ascii=False,
            )
        )
        return 0

    raw = args.input_jsonl.read_text(encoding="utf-8")
    existing = _existing_person_ids(args.target_jsonl)
    promoted: list[dict[str, Any]] = []
    errors: list[str] = []
    skip_unverified = 0
    skip_duplicate = 0
    actions: list[dict[str, Any]] = []

    for line_no, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {line_no}: json: {e}")
            continue
        if not isinstance(obj, dict):
            errors.append(f"line {line_no}: row must be object")
            continue

        digest_src = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(digest_src.encode("utf-8")).hexdigest()
        pid = _person_id(obj, line_no=line_no, payload_digest=digest)

        if not _has_verified_provenance(obj):
            skip_unverified += 1
            actions.append({"action": "SKIP_UNVERIFIED", "line": line_no, "person_id": pid})
            continue

        if pid in existing:
            skip_duplicate += 1
            actions.append({"action": "SKIP_DUPLICATE", "line": line_no, "person_id": pid})
            continue

        birth = _birth_instant(obj)
        if not birth:
            errors.append(f"line {line_no}: missing birth_instant_utc / dob_utc")
            continue
        if not _ISO_Z.match(birth):
            errors.append(f"line {line_no}: birth instant must be ISO8601 ending with Z")
            continue

        tz = str(obj.get("iana_tz") or "").strip() or "Etc/UTC"
        tz_defaulted = not str(obj.get("iana_tz") or "").strip()

        bm = _parse_bool_male(obj)
        if bm is None:
            errors.append(f"line {line_no}: is_male or sex (m/f) required")
            continue

        try:
            birth_doc = _run_birth_cli(birth, tz, bm)
        except Exception as e:
            errors.append(f"line {line_no} person_id={pid}: {e}")
            continue

        saj = birth_doc.get("full_saju", {}).get("saju", {})
        pillars = {k: str(saj.get(k) or "") for k in ("year", "month", "day", "hour")} if isinstance(saj, dict) else {}

        sko = str(obj.get("sasang_label_ko") or "").strip()
        sen = str(obj.get("sasang_label_en") or "").strip()
        quote = str(obj.get("source_citation") or "").strip()[:2000]
        pmids = obj.get("literature_catalog_pmids")
        pmid_list: list[str] = []
        if isinstance(pmids, list):
            pmid_list = [str(x).strip() for x in pmids if str(x).strip()]

        url = str(obj.get("provenance_url") or obj.get("source_url") or "").strip()
        cite = str(obj.get("source_citation") or "").strip()
        prov_tag = str(obj.get("provenance") or "").strip()

        sasang_const = None
        if sko or sen:
            sasang_const = {
                "label_ko": sko or None,
                "label_en": sen or None,
                "confidence": 0.85,
                "source": {
                    "pmid": pmid_list[0] if pmid_list else None,
                    "quote": quote or None,
                    "method": "curated_saju_joint_v1",
                    "provenance_url": url or None,
                },
            }

        provenance_doc = (
            f"ingest_curated_saju_joint_v1.py from {args.input_jsonl.name} line {line_no}; "
            f"url={bool(url)} citation={bool(cite)} tag={prov_tag or '—'}"
        )
        if tz_defaulted:
            provenance_doc += "; iana_tz defaulted to Etc/UTC"

        note = str(obj.get("note") or "").strip()
        exp_in = obj.get("expectations")
        expectations_out: dict[str, Any] | None = exp_in if isinstance(exp_in, dict) else None

        out_row: dict[str, Any] = {
            "schema": "sasang_saju_joint_benchmark_row_v1",
            "person_id": pid,
            "display_name": _display_name(obj, line_no=line_no, fallback_id=pid),
            "benchmark_tier": "curated_saju_joint_v1",
            "privacy_tier": "curator_attested_provenance_v1",
            "provenance": provenance_doc,
            "sasang_constitution": sasang_const,
            "birth_resolution": {
                "birth_instant_utc": birth,
                "iana_tz": tz,
                "is_male": bm,
                **({"tz_defaulted_utc": True} if tz_defaulted else {}),
            },
            "saju_engine_output_v1": {"pillars": pillars, "resolution": birth_doc.get("resolution")},
            "literature_catalog_pmids": pmid_list,
            "expectations": expectations_out,
        }
        if note:
            out_row["curator_note"] = note[:2000]

        promoted.append(out_row)
        existing.add(pid)
        actions.append({"action": "APPEND", "line": line_no, "person_id": pid})

    summary = {
        "ok": not errors,
        "appended": len(promoted),
        "skip_unverified": skip_unverified,
        "skip_duplicate": skip_duplicate,
        "errors": errors,
        "actions": actions,
        "target": str(args.target_jsonl),
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, **summary}, ensure_ascii=False, indent=2))
        return 1 if errors else 0

    if promoted:
        args.target_jsonl.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if args.target_jsonl.is_file() else "w"
        with args.target_jsonl.open(mode, encoding="utf-8") as outf:
            for r in promoted:
                outf.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
