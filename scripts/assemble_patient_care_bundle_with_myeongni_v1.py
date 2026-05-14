#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assemble `patient_care_bundle_v1` JSON: run `build_myeongni_full_report_v1`, attach path in
`provenance.myeongni_report_path`, and fill patient_slots (stub SOAP + lens slots).

Clinical SOAP text must be replaced or supplied via --soap-json by the physician workflow.

Optional post-write steps (order: --apply-slot-templates, --validate-policy, --render-md-out):
slot templates from `docs/final/artifacts/patient_care_bundle_slot_templates_ko_v1.json`,
default policy `patient_care_bundle_generation_policy_v1.default.json`, single Markdown render.
Successful post steps append audit fields under `provenance` (UTC + workspace-relative paths).
Final `--validate` runs jsonschema on the written bundle (including audit fields).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MYEONGNI_BUILDER = ROOT / "scripts" / "build_myeongni_full_report_v1.py"
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "patient_care_bundle_v1.schema.json"
APPLY_SLOT_TEMPLATES = ROOT / "scripts" / "apply_patient_care_bundle_slot_templates_v1.py"
VALIDATE_POLICY = ROOT / "scripts" / "validate_patient_care_bundle_against_policy_v1.py"
RENDER_BUNDLE_MD = ROOT / "scripts" / "render_patient_care_bundle_markdown_v1.py"
DEFAULT_POLICY_JSON = ROOT / "docs" / "final" / "artifacts" / "patient_care_bundle_generation_policy_v1.default.json"
SLOT_TEMPLATES_JSON = ROOT / "docs" / "final" / "artifacts" / "patient_care_bundle_slot_templates_ko_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_workspace(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _run_myeongni_report(
    local_ymdhms: tuple[int, int, int, int, int, int],
    iana_tz: str,
    is_male: bool,
    out_json: Path,
    annual_start_year: int,
    annual_years: int,
    monthly_months: int,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(MYEONGNI_BUILDER),
        "--local",
        *[str(x) for x in local_ymdhms],
        "--iana-tz",
        iana_tz,
        "--annual-start-year",
        str(annual_start_year),
        "--annual-years",
        str(annual_years),
        "--monthly-months-per-year",
        str(monthly_months),
        "--out-json",
        str(out_json),
    ]
    if is_male:
        cmd.append("--is-male")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout or "myeongni build failed")
    return json.loads(out_json.read_text(encoding="utf-8-sig"))


def _stub_soap() -> dict[str, Any]:
    stub = (
        "[STUB] 한의사 최종 소견을 반영해 교체하십시오. "
        "본 필드는 `assemble_patient_care_bundle_with_myeongni_v1.py` 기본값입니다."
    )
    return {
        "subjective": {"text": stub},
        "objective": {"text": stub},
        "assessment": {"text": stub},
        "plan": {"text": stub},
    }


def _load_soap_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    out: dict[str, Any] = {}
    for k in ("subjective", "objective", "assessment", "plan"):
        v = raw.get(k)
        if isinstance(v, str):
            out[k] = {"text": v}
        elif isinstance(v, dict) and isinstance(v.get("text"), str):
            out[k] = {"text": v["text"]}
        else:
            raise SystemExit(f"soap-json missing string or {{text}} for {k}")
    return out


def _myeongni_slot_body(report: dict[str, Any], rel_path: str) -> str:
    pillars = report.get("pillars") or {}
    y = pillars.get("year", "?")
    m = pillars.get("month", "?")
    d = pillars.get("day", "?")
    h = pillars.get("hour", "?")
    dm = (report.get("day_master") or {}).get("stem_hangul", "?")
    lines = [
        "## 명리 참고 [HYPO]",
        "",
        f"- 사주 원국(엔진): **년** {y} · **월** {m} · **일** {d} · **시** {h} · **일간** {dm}",
        f"- 전체 리포트(JSON): `{rel_path}` (`build_myeongni_full_report_v1` 산출)",
        "",
        "임상 예후·임신 시기와 인과로 읽지 마십시오. 일정·심리 정리용입니다.",
    ]
    return "\n".join(lines)


def _build_bundle(
    *,
    myeongni_report: dict[str, Any],
    myeongni_rel: str,
    soap: dict[str, Any],
    generator_id: str,
    generator_version: str,
    opinion_sha256: str | None,
    cds_envelope_rel: str | None = None,
    cds_envelope_sha256: str | None = None,
) -> dict[str, Any]:
    hypo = (
        "[HYPO] 명리는 임상 예후·임신 성공을 예측하지 않습니다. "
        "캘린더·심리 정리용입니다."
    )
    logos_ack = (
        "[NON_GATING] Logos 슬롯은 임상 결정을 바꾸지 않는 상징·가치 정렬 문구만 허용."
    )
    bundle: dict[str, Any] = {
        "schema": "patient_care_bundle_v1",
        "version": "1.0.0",
        "bundle_id": str(uuid.uuid4()),
        "generated_at_utc": _now_utc(),
        "provenance": {
            "generator_id": generator_id,
            "generator_version": generator_version,
            "myeongni_report_path": myeongni_rel,
        },
        "boundary_contract": {
            "physician_final_authority": True,
            "clinical_slots_separate_from_lens": True,
            "myeongni_hypo_only": True,
            "logos_non_gating_only": True,
        },
        "clinical_soap_v1": soap,
        "patient_slots": [
            {
                "slot_order": 0,
                "slot_id": "core",
                "trust_tier": "clinical_reference",
                "included": True,
                "title": "진료 요약 및 생활 안내",
                "body_markdown": (
                    "한의사 최종 소견을 바탕으로 한 환자용 요약을 여기에 기재하십시오. "
                    "현재 SOAP는 스텁이면 `core`와 함께 교체하는 것이 좋습니다."
                ),
            },
            {
                "slot_order": 1,
                "slot_id": "sasang",
                "trust_tier": "clinical_reference",
                "included": True,
                "title": "체질·생활 리듬 (사상의학)",
                "body_markdown": (
                    "한의사가 승인한 체질별 일상 조절(수면·식사·운동 강도)을 기재하십시오. "
                    "미기재 시 `included`를 false로 두고 본문을 비울 수 있습니다."
                ),
            },
            {
                "slot_order": 2,
                "slot_id": "myeongni_ref",
                "trust_tier": "hypo_reference",
                "included": True,
                "title": "일정·마음 참고 [HYPO]",
                "hypo_ack": hypo,
                "body_markdown": _myeongni_slot_body(myeongni_report, myeongni_rel),
            },
            {
                "slot_order": 3,
                "slot_id": "logos_opt",
                "trust_tier": "non_gating_symbolic",
                "included": False,
                "title": "선택 해설 (Logos)",
                "non_gating_ack": logos_ack,
                "body_markdown": "",
            },
        ],
        "disclaimers": [
            "본 문서는 참고용이며 응급 처치를 대체하지 않습니다. 증상 악화 시 의료기관에 내원하십시오.",
            "명리·Logos 슬롯은 [HYPO]/[NON_GATING]이며 진단·치료·임신 시기 예측 근거가 될 수 없습니다.",
            "SOAP 및 core 슬롯은 담당 한의사의 최종 확인 후 환자에게 제공하십시오.",
        ],
    }
    if opinion_sha256:
        bundle["provenance"]["physician_opinion_sha256"] = opinion_sha256
    if cds_envelope_rel and cds_envelope_sha256:
        bundle["provenance"]["km_cds_envelope_path"] = cds_envelope_rel
        bundle["provenance"]["km_cds_envelope_sha256"] = cds_envelope_sha256
    return bundle


def _optional_sha256(path: Path | None) -> str | None:
    if path is None:
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _run_helper_script(script: Path, argv: list[str], *, what: str) -> None:
    if not script.is_file():
        raise SystemExit(f"missing helper script: {script} ({what})")
    cmd = [sys.executable, str(script), *argv]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        msg = (cp.stderr or "") + (cp.stdout or "")
        raise SystemExit(f"{what} failed (exit {cp.returncode}): {msg.strip()}")


def _merge_post_process_provenance(
    bundle_path: Path,
    *,
    slot_templates: bool,
    policy_validated: bool,
    policy_json: Path | None,
    markdown_out: Path | None,
) -> None:
    extra: dict[str, str] = {}
    if slot_templates:
        extra["slot_templates_applied_utc"] = _now_utc()
        extra["slot_templates_json_path"] = _rel_workspace(SLOT_TEMPLATES_JSON)
    if policy_validated and policy_json is not None:
        extra["generation_policy_validated_utc"] = _now_utc()
        extra["generation_policy_json_path"] = _rel_workspace(policy_json)
    if markdown_out is not None:
        extra["patient_facing_markdown_written_utc"] = _now_utc()
        extra["patient_facing_markdown_path"] = _rel_workspace(markdown_out)
    if not extra:
        return
    doc = json.loads(bundle_path.read_text(encoding="utf-8-sig"))
    prov = doc.setdefault("provenance", {})
    prov.update(extra)
    bundle_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build myeongni_full_report JSON and assemble patient_care_bundle_v1 with pointer."
    )
    ap.add_argument("--local", nargs=6, type=int, required=True, metavar=("Y", "M", "D", "h", "m", "s"))
    ap.add_argument("--iana-tz", default="Asia/Seoul")
    ap.add_argument("--is-male", action="store_true")
    ap.add_argument(
        "--myeongni-out",
        type=Path,
        default=ROOT / "reports" / "patient_care_myeongni_full_for_bundle_latest.json",
        help="Written myeongni_full_report_v1 JSON path",
    )
    ap.add_argument(
        "--bundle-out",
        type=Path,
        default=ROOT / "reports" / "patient_care_bundle_with_myeongni_latest.json",
        help="Output patient_care_bundle_v1 JSON path",
    )
    ap.add_argument("--annual-start-year", type=int, default=datetime.now().year)
    ap.add_argument("--annual-years", type=int, default=5)
    ap.add_argument("--monthly-months-per-year", type=int, default=12)
    ap.add_argument("--soap-json", type=Path, help="SOAP fields JSON (see tests/fixtures/patient_care_bundle_soap_stub_v1.example.json)")
    ap.add_argument(
        "--cds-envelope-json",
        type=Path,
        help="Optional km_physician_cds_assist_envelope_v1 JSON; path+SHA-256 recorded in provenance",
    )
    ap.add_argument("--physician-opinion-file", type=Path, help="Optional file to hash into provenance")
    ap.add_argument("--generator-id", default="assemble_patient_care_bundle_with_myeongni_v1")
    ap.add_argument("--generator-version", default="1.0.0")
    ap.add_argument("--validate", action="store_true", help="Validate output against patient_care_bundle_v1 schema")
    ap.add_argument(
        "--apply-slot-templates",
        action="store_true",
        help="After write: run apply_patient_care_bundle_slot_templates_v1 (--myeongni-json = --myeongni-out)",
    )
    ap.add_argument(
        "--validate-policy",
        action="store_true",
        help="After write (and optional templates): run validate_patient_care_bundle_against_policy_v1",
    )
    ap.add_argument(
        "--policy-json",
        type=Path,
        default=None,
        help="Policy JSON for --validate-policy (default: patient_care_bundle_generation_policy_v1.default.json)",
    )
    ap.add_argument(
        "--render-md-out",
        type=Path,
        default=None,
        help="After policy pass: write single Markdown via render_patient_care_bundle_markdown_v1",
    )
    args = ap.parse_args()

    local_tuple = (args.local[0], args.local[1], args.local[2], args.local[3], args.local[4], args.local[5])
    report = _run_myeongni_report(
        local_tuple,
        args.iana_tz,
        args.is_male,
        args.myeongni_out,
        args.annual_start_year,
        args.annual_years,
        args.monthly_months_per_year,
    )
    soap = _load_soap_json(args.soap_json) if args.soap_json else _stub_soap()
    rel = _rel_workspace(args.myeongni_out)
    opinion_hash = _optional_sha256(args.physician_opinion_file)
    cds_rel: str | None = None
    cds_sha: str | None = None
    if args.cds_envelope_json:
        cds_rel = _rel_workspace(args.cds_envelope_json)
        cds_sha = _optional_sha256(args.cds_envelope_json)
        if not cds_sha:
            raise SystemExit("cds-envelope-json could not be hashed")
    bundle = _build_bundle(
        myeongni_report=report,
        myeongni_rel=rel,
        soap=soap,
        generator_id=args.generator_id,
        generator_version=args.generator_version,
        opinion_sha256=opinion_hash,
        cds_envelope_rel=cds_rel,
        cds_envelope_sha256=cds_sha,
    )

    args.bundle_out.parent.mkdir(parents=True, exist_ok=True)
    args.bundle_out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    rel_mye = _rel_workspace(args.myeongni_out)
    policy_json_resolved: Path | None = None
    if args.apply_slot_templates:
        _run_helper_script(
            APPLY_SLOT_TEMPLATES,
            [
                "--bundle-in",
                str(args.bundle_out),
                "--bundle-out",
                str(args.bundle_out),
                "--myeongni-json",
                str(args.myeongni_out),
                "--myeongni-report-rel",
                rel_mye,
            ],
            what="apply_slot_templates",
        )
    if args.validate_policy:
        policy_json_resolved = args.policy_json if args.policy_json is not None else DEFAULT_POLICY_JSON
        if not policy_json_resolved.is_file():
            raise SystemExit(f"policy-json not found: {policy_json_resolved}")
        _run_helper_script(
            VALIDATE_POLICY,
            ["--bundle-json", str(args.bundle_out), "--policy-json", str(policy_json_resolved)],
            what="validate_policy",
        )
    if args.render_md_out is not None:
        _run_helper_script(
            RENDER_BUNDLE_MD,
            ["--bundle-json", str(args.bundle_out), "--out-md", str(args.render_md_out)],
            what="render_markdown",
        )

    _merge_post_process_provenance(
        args.bundle_out,
        slot_templates=args.apply_slot_templates,
        policy_validated=args.validate_policy,
        policy_json=policy_json_resolved,
        markdown_out=args.render_md_out,
    )

    if args.validate:
        try:
            import jsonschema
        except ImportError as e:
            raise SystemExit("jsonschema required for --validate") from e
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        final_doc = json.loads(args.bundle_out.read_text(encoding="utf-8-sig"))
        jsonschema.validate(instance=final_doc, schema=schema)

    print(json.dumps({"ok": True, "bundle_out": str(args.bundle_out), "myeongni_out": str(args.myeongni_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
