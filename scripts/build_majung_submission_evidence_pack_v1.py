#!/usr/bin/env python3
"""Build Majung K-Startup submission evidence pack (E1–E4 + E2E demo index)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

EVIDENCE_ITEMS: list[dict[str, str]] = [
    {
        "id": "E1",
        "path": "docs/final/artifacts/compression_enterprise_executive_summary_v1.md",
        "purpose": "Compression bench and governance (Track A frozen bench narrative)",
    },
    {
        "id": "E2",
        "path": "docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md",
        "purpose": "Macro observation API SKU (B2B one-pager)",
    },
    {
        "id": "E3",
        "path": "docs/final/artifacts/macro_risk_warning_api_smoke_latest.json",
        "purpose": "API contract smoke snapshot",
    },
    {
        "id": "E4",
        "path": "docs/final/artifacts/compression_board_ms_correlation_report_v1_latest.json",
        "purpose": "RQ-017 footnote only — correlation_claim_allowed must stay false",
        "optional": "true",
    },
    {
        "id": "E2E",
        "path": "docs/final/artifacts/majung_e2e_demo_latest.md",
        "purpose": "Integrated FinOps + macro WATCH + gate chain summary",
    },
    {
        "id": "E2E_JSON",
        "path": "docs/final/artifacts/majung_e2e_demo_latest.json",
        "purpose": "Machine-readable E2E demo bundle",
    },
]

DEFAULT_OUT_DIR = ROOT / "reports" / "majung_submission_evidence_pack_v1"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/majung_submission_evidence_pack_manifest_latest.json"


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def _copy_item(src: Path, dest_dir: Path) -> Path | None:
    if not src.is_file():
        return None
    dest = dest_dir / f"{src.stem}{src.suffix}"
    shutil.copy2(src, dest)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble Majung submission evidence pack directory.")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--no-copy", action="store_true", help="Index only; do not copy files into out-dir")
    args = ap.parse_args()

    out_dir: Path = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    missing_required: list[str] = []

    for item in EVIDENCE_ITEMS:
        rel = item["path"]
        src = ROOT / rel
        optional = item.get("optional") == "true"
        entry: dict[str, Any] = {
            "id": item["id"],
            "source_path": rel,
            "purpose": item["purpose"],
            "optional": optional,
            "exists": src.is_file(),
        }
        if not src.is_file():
            if not optional:
                missing_required.append(rel)
            entries.append(entry)
            continue

        if not args.no_copy:
            copied = _copy_item(src, out_dir)
            if copied:
                entry["pack_copy"] = _rel(copied)

        if item["id"] == "E4":
            doc = json.loads(src.read_text(encoding="utf-8-sig"))
            derived = doc.get("derived") if isinstance(doc.get("derived"), dict) else {}
            entry["rq017_correlation_claim_allowed"] = derived.get("correlation_claim_allowed")
            if derived.get("correlation_claim_allowed") is True:
                entry["warning"] = "E4 must not be used for ms-token causal claims in submission"

        entries.append(entry)

    index_lines = [
        "# Majung submission evidence pack (internal PDF source)",
        "",
        f"- **generated_at_utc:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **program:** K-Startup global enterprise collaboration (Microsoft), pbancSn 177575",
        f"- **ready_for_external_send:** false — legal / G0 human gates still required",
        "",
        "## Files in this folder",
        "",
    ]
    for e in entries:
        status = "OK" if e.get("exists") else ("SKIP optional" if e.get("optional") else "MISSING")
        copy_name = e.get("pack_copy") or "—"
        index_lines.append(f"- **{e['id']}** [{status}] `{e['source_path']}`")
        if e.get("pack_copy"):
            index_lines.append(f"  - copy: `{copy_name}`")
        index_lines.append(f"  - {e['purpose']}")
        if e.get("rq017_correlation_claim_allowed") is False:
            index_lines.append("  - RQ-017: correlation_claim_allowed=false (footnote only)")
        index_lines.append("")

    index_lines.extend(
        [
            "## Submission copy rules (do not paste into K-Startup without review)",
            "",
            "- No selection guarantee, trading alpha, Prophecy Sandbox branding.",
            "- 47% only with frozen 40-case bench + floor 0.47; finance_macro % is separate PoC corpus.",
            "- Do not claim MS official partner status before selection.",
            "",
            "## 10-minute demo order",
            "",
            "1. Problem (FinOps / grounding) — E1 or E2E summary",
            "2. Macro API WATCH — E3 JSON",
            "3. Frozen bench ~47.5% / 40 cases — E1",
            "4. Finance workload PoC (separate corpus) — E2E JSON finance_workload block",
            "5. Gate chain PASS — E2E chain_steps",
            "",
        ]
    )

    index_path = out_dir / "INDEX.md"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    manifest: dict[str, Any] = {
        "schema": "majung_submission_evidence_pack_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pack_directory": _rel(out_dir),
        "index_path": _rel(index_path),
        "entries": entries,
        "missing_required": missing_required,
        "pack_ok": len(missing_required) == 0,
        "boundary_ack": "Pack assembly does not imply K-Startup selection or eligibility pass.",
    }

    manifest_out = args.manifest_out if args.manifest_out.is_absolute() else ROOT / args.manifest_out
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"majung_evidence_pack: index -> {index_path}")
    print(f"majung_evidence_pack: manifest -> {manifest_out}")
    print(f"majung_evidence_pack: pack_ok={manifest['pack_ok']} missing={missing_required}")
    return 0 if manifest["pack_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
