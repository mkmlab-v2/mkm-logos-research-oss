#!/usr/bin/env python3
# Keywords: showroom, cdim, logos_cross_domain, non_gating
"""Public showroom JSON slice for Logos CDIM v1 (read-only, no ohaeng on corpus)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CDIM = ROOT / "docs" / "final" / "artifacts" / "logos_cross_domain_interface_latest.json"
DEFAULT_OUT = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "ops"
    / "windows-rehearsal"
    / "jemaai-cloud-mvp"
    / "showroom_logos_cross_domain_interface_slice_v1.json"
)


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def build_slice(cdim: dict[str, Any] | None, *, source_rel: str) -> dict[str, Any]:
    if not cdim or cdim.get("schema") != "logos_cross_domain_interface_v1":
        return {
            "schema": "showroom_logos_cross_domain_interface_slice_v1",
            "version": "1.0.0",
            "state": "NODATA",
            "source_rel": source_rel,
            "role": "logos_cross_domain_interface_v1",
            "non_gating": True,
            "research_only": True,
        }
    csum = cdim.get("conflict_summary") if isinstance(cdim.get("conflict_summary"), dict) else {}
    return {
        "schema": "showroom_logos_cross_domain_interface_slice_v1",
        "version": "1.0.0",
        "state": "OK",
        "generated_at_utc": _utc_now_z(),
        "source_rel": source_rel,
        "role": "logos_cross_domain_interface_v1",
        "non_gating": True,
        "research_only": True,
        "cdim_ts_utc": cdim.get("ts_utc"),
        "field_regime_id": cdim.get("field_regime_id"),
        "no_verse_level_ohaeng_ingest": cdim.get("no_verse_level_ohaeng_ingest"),
        "lens_direction_signs": [
            str((s or {}).get("direction_sign"))
            for s in (cdim.get("lens_snapshots") or [])
            if isinstance(s, dict)
        ],
        "cross_ref_count": len(cdim.get("cross_refs") or []),
        "minority_lens_ids": csum.get("minority_lens_ids"),
        "forbidden_claims": cdim.get("forbidden_claims"),
        "design_doc": cdim.get("design_doc"),
        "boundary_note": "Lens isolation only; not prophecy hit rate or live trading.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdim-json", type=Path, default=DEFAULT_CDIM)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--mirror-staging", action="store_true")
    args = ap.parse_args()
    cdim = _read_json(args.cdim_json)
    doc = build_slice(cdim, source_rel=_rel(args.cdim_json))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mirrored: list[str] = []
    if args.mirror_staging:
        staging = ROOT / "projects" / "bitcoin-trading" / "ops" / "windows-rehearsal" / ".showroom_staging"
        staging.mkdir(parents=True, exist_ok=True)
        import shutil

        dest = staging / args.out.name
        shutil.copy2(args.out, dest)
        mirrored.append(str(dest))
    print(json.dumps({"ok": True, "out": _rel(args.out), "state": doc.get("state"), "mirrored": mirrored}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
