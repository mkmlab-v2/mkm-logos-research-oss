#!/usr/bin/env python3
"""Track L L0 readiness: charter paths, corpus manifest, verse resolver smoke (John 19:34 → Jhn.19.34)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHARTER = ROOT / "docs/final/LOGOS_HERMENEUTICS_TRACK_L_CHARTER_V1.md"
CHECKLIST = ROOT / "docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md"
MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
RESOLVER = ROOT / "scripts/resolve_logos_verse_reference_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_l_l0_readiness_v1_latest.json"
EXPECTED_VERSE = "Jhn.19.34"
EXPECTED_VERSE_COUNT = 31102


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _check_file(path: Path, label: str, checks: list[dict[str, Any]]) -> bool:
    ok = path.is_file()
    checks.append({"id": label, "path": _rel(path), "ok": ok})
    return ok


def _check_manifest(checks: list[dict[str, Any]]) -> bool:
    if not MANIFEST.is_file():
        checks.append({"id": "corpus_manifest", "path": _rel(MANIFEST), "ok": False})
        return False
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        checks.append(
            {
                "id": "corpus_manifest",
                "path": _rel(MANIFEST),
                "ok": False,
                "error": str(e)[:200],
            }
        )
        return False
    count = data.get("verse_count") or data.get("row_count")
    ok = count == EXPECTED_VERSE_COUNT
    checks.append(
        {
            "id": "corpus_manifest",
            "path": _rel(MANIFEST),
            "ok": ok,
            "verse_count": count,
            "expected": EXPECTED_VERSE_COUNT,
        }
    )
    return ok


def _check_resolver_smoke(checks: list[dict[str, Any]]) -> bool:
    if not RESOLVER.is_file():
        checks.append({"id": "resolver_script", "path": _rel(RESOLVER), "ok": False})
        return False
    proc = subprocess.run(
        [sys.executable, str(RESOLVER), "John 19:34"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    primary: str | None = None
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            doc = json.loads(proc.stdout)
            primary = doc.get("primary_verse_id")
        except json.JSONDecodeError:
            pass
    ok = proc.returncode == 0 and primary == EXPECTED_VERSE
    checks.append(
        {
            "id": "resolver_john_19_34",
            "path": _rel(RESOLVER),
            "ok": ok,
            "exit_code": proc.returncode,
            "primary_verse_id": primary,
            "expected": EXPECTED_VERSE,
        }
    )
    return ok


def _check_corpus_row(checks: list[dict[str, Any]]) -> bool:
    if not JSONL.is_file():
        checks.append({"id": "corpus_jsonl", "path": _rel(JSONL), "ok": False})
        return False
    import importlib.util

    spec = importlib.util.spec_from_file_location("resolve_logos_verse_reference_v1", RESOLVER)
    if spec is None or spec.loader is None:
        checks.append({"id": "corpus_row_jhn_19_34", "ok": False, "error": "import_spec_failed"})
        return False
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    row = mod.load_verse_row(EXPECTED_VERSE, JSONL)
    ok = row is not None and row.get("verse_id") == EXPECTED_VERSE
    greek_hint = None
    if row:
        text = json.dumps(row, ensure_ascii=False)
        greek_hint = ("αἷμα" in text or "ὕδωρ" in text or "αιμα" in text.lower())
    checks.append(
        {
            "id": "corpus_row_jhn_19_34",
            "path": _rel(JSONL),
            "ok": ok,
            "greek_blood_water_hint": greek_hint,
        }
    )
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    checks: list[dict[str, Any]] = []
    gates = [
        _check_file(CHARTER, "charter_md", checks),
        _check_file(CHECKLIST, "checklist_md", checks),
        _check_manifest(checks),
        _check_resolver_smoke(checks),
        _check_corpus_row(checks),
    ]
    l0_ok = all(gates)

    doc: dict[str, Any] = {
        "schema": "logos_track_l_l0_readiness_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "track": "L",
        "gate_level": "L0",
        "l0_ok": l0_ok,
        "track_wall": {
            "a_track_live_trigger": False,
            "compression_kpi_merge": False,
            "logos_non_gating": True,
        },
        "checks": checks,
        "contract_path": "docs/final/artifacts/LOGOS_TRACK_L_L0_READINESS_V1_CONTRACT.json",
    }

    if not args.stdout_only:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if l0_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
