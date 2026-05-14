#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chain: validate `km_physician_cds_assist_envelope_v1` JSON, then run
`assemble_patient_care_bundle_with_myeongni_v1` (records CDS path + SHA-256 in bundle provenance).

Does not merge CDS narrative into SOAP; supply `--soap-json` from physician workflow.

Optional flags `--apply-slot-templates`, `--validate-policy`, `--policy-json`, `--render-md-out`
are forwarded to assemble (see that script).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CDS_SCHEMA = ROOT / "docs" / "final" / "schemas" / "km_physician_cds_assist_envelope_v1.schema.json"
ASSEMBLE = ROOT / "scripts" / "assemble_patient_care_bundle_with_myeongni_v1.py"
DEFAULT_SOAP = ROOT / "tests" / "fixtures" / "patient_care_bundle_soap_stub_v1.example.json"


def _validate_cds(doc: dict, schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError as e:
        raise SystemExit("jsonschema required for CDS validation") from e
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate KM CDS envelope then assemble patient_care_bundle_v1")
    ap.add_argument("--cds-envelope-json", type=Path, required=True, help="km_physician_cds_assist_envelope_v1 JSON")
    ap.add_argument("--cds-schema", type=Path, default=CDS_SCHEMA)
    ap.add_argument("--local", nargs=6, type=int, required=True, metavar=("Y", "M", "D", "h", "m", "s"))
    ap.add_argument("--iana-tz", default="Asia/Seoul")
    ap.add_argument("--is-male", action="store_true")
    ap.add_argument(
        "--soap-json",
        type=Path,
        default=None,
        help="SOAP JSON; default: tests/fixtures/patient_care_bundle_soap_stub_v1.example.json",
    )
    ap.add_argument(
        "--myeongni-out",
        type=Path,
        default=ROOT / "reports" / "patient_care_myeongni_full_for_bundle_latest.json",
    )
    ap.add_argument(
        "--bundle-out",
        type=Path,
        default=ROOT / "reports" / "patient_care_bundle_with_myeongni_latest.json",
    )
    ap.add_argument("--annual-start-year", type=int, default=None)
    ap.add_argument("--annual-years", type=int, default=5)
    ap.add_argument("--monthly-months-per-year", type=int, default=12)
    ap.add_argument("--skip-cds-schema-validation", action="store_true")
    ap.add_argument("--validate-bundle", action="store_true", help="Pass --validate to assemble (jsonschema)")
    ap.add_argument("--physician-opinion-file", type=Path, default=None)
    ap.add_argument(
        "--apply-slot-templates",
        action="store_true",
        help="Forward to assemble: apply KO slot templates after write",
    )
    ap.add_argument(
        "--validate-policy",
        action="store_true",
        help="Forward to assemble: run generation policy gate",
    )
    ap.add_argument(
        "--policy-json",
        type=Path,
        default=None,
        help="Forward to assemble: policy JSON (with --validate-policy)",
    )
    ap.add_argument(
        "--render-md-out",
        type=Path,
        default=None,
        help="Forward to assemble: write Markdown after policy pass",
    )
    args = ap.parse_args()

    env_path = args.cds_envelope_json
    doc = json.loads(env_path.read_text(encoding="utf-8-sig"))
    if not args.skip_cds_schema_validation:
        _validate_cds(doc, args.cds_schema)

    soap_path = args.soap_json if args.soap_json is not None else DEFAULT_SOAP
    if not soap_path.is_file():
        raise SystemExit(f"soap-json not found: {soap_path}")

    y0 = args.annual_start_year if args.annual_start_year is not None else datetime.now().year

    cmd = [
        sys.executable,
        str(ASSEMBLE),
        "--local",
        *[str(x) for x in args.local],
        "--iana-tz",
        args.iana_tz,
        "--myeongni-out",
        str(args.myeongni_out),
        "--bundle-out",
        str(args.bundle_out),
        "--annual-start-year",
        str(y0),
        "--annual-years",
        str(args.annual_years),
        "--monthly-months-per-year",
        str(args.monthly_months_per_year),
        "--soap-json",
        str(soap_path),
        "--cds-envelope-json",
        str(env_path.resolve()),
    ]
    if args.is_male:
        cmd.append("--is-male")
    if args.physician_opinion_file:
        cmd.extend(["--physician-opinion-file", str(args.physician_opinion_file)])
    if args.validate_bundle:
        cmd.append("--validate")
    if args.apply_slot_templates:
        cmd.append("--apply-slot-templates")
    if args.validate_policy:
        cmd.append("--validate-policy")
    if args.policy_json is not None:
        cmd.extend(["--policy-json", str(args.policy_json)])
    if args.render_md_out is not None:
        cmd.extend(["--render-md-out", str(args.render_md_out)])

    cp = subprocess.run(cmd, cwd=str(ROOT))
    return int(cp.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
