#!/usr/bin/env python3
"""Stage C smoke: KM classics citation + CDS bundle chain + policy gate [HYPO]."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/build_patient_care_bundle_from_km_cds_chain_v1.py"
VALIDATE = ROOT / "scripts/validate_patient_care_bundle_against_policy_v1.py"
CDS_FIXTURE = ROOT / "tests/fixtures/km_physician_cds_assist_envelope_v1.example.json"
SOAP_FIXTURE = ROOT / "tests/fixtures/patient_care_bundle_soap_stub_v1.example.json"
INDEX_STUB = ROOT / "tests/fixtures/km_classics_index_hypo_v1.stub.json"
DEFAULT_OUT = ROOT / "reports/km_classics_citation_cds_smoke_v1_latest.json"


def run_smoke(*, root: Path = ROOT, out_json: Path = DEFAULT_OUT) -> dict:
    if not all(p.is_file() for p in (CHAIN, VALIDATE, CDS_FIXTURE, SOAP_FIXTURE, INDEX_STUB)):
        missing = [str(p) for p in (CHAIN, VALIDATE, CDS_FIXTURE, SOAP_FIXTURE, INDEX_STUB) if not p.is_file()]
        raise FileNotFoundError(f"missing: {missing}")

    work = root / "reports" / "_km_classics_citation_cds_smoke_work"
    work.mkdir(parents=True, exist_ok=True)
    mye = work / "myeongni.json"
    bundle = work / "bundle.json"

    first_id = json.loads(INDEX_STUB.read_text(encoding="utf-8"))["entries"][0]["source_id"]

    cmd = [
        sys.executable,
        str(CHAIN),
        "--cds-envelope-json",
        str(CDS_FIXTURE),
        "--local",
        "1994",
        "4",
        "10",
        "11",
        "2",
        "0",
        "--iana-tz",
        "Asia/Seoul",
        "--soap-json",
        str(SOAP_FIXTURE),
        "--myeongni-out",
        str(mye),
        "--bundle-out",
        str(bundle),
        "--annual-start-year",
        "2026",
        "--annual-years",
        "1",
        "--monthly-months-per-year",
        "3",
        "--validate-bundle",
        "--classic-index-json",
        str(INDEX_STUB),
        "--classic-source-ids",
        first_id,
        "--append-classics-audit",
        "--request-id",
        "smoke-v1",
    ]
    cp = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"cds_chain_failed: {cp.stderr}\n{cp.stdout}")

    doc = json.loads(bundle.read_text(encoding="utf-8-sig"))
    refs = (doc.get("provenance") or {}).get("classic_refs") or []
    if not refs or not all(r.get("citation_valid") for r in refs):
        raise RuntimeError("classic_refs_missing_or_invalid")

    vcmd = [sys.executable, str(VALIDATE), "--bundle-json", str(bundle)]
    vcp = subprocess.run(vcmd, cwd=str(root), capture_output=True, text=True)
    if vcp.returncode != 0:
        raise RuntimeError(f"policy_validate_failed: {vcp.stderr}\n{vcp.stdout}")

    report = {
        "schema": "km_classics_citation_cds_smoke_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "clinician_lane_only": True,
        "personadiary_join": False,
        "ok": True,
        "classic_source_id": first_id,
        "classic_refs_count": len(refs),
        "bundle_path": str(bundle.relative_to(root)).replace("\\", "/"),
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    try:
        report = run_smoke(out_json=args.out_json)
    except (FileNotFoundError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
