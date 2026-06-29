"""
Append consumer_survey_only clinic MVP captures (mkmlife-style surfaces).

Physician label stays withheld. Score via clinic_constitution_survey_item_bank_v1.
Optional registry backfill from patient intake (pseudo-responses — bootstrap only).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.clinic_constitution_mvp_ledger_v1 import append_clinic_capture_line  # noqa: E402
from scripts.import_clinic_mvp_from_patient_registry_v1 import (  # noqa: E402
    REGISTRY_REL,
    iter_clinical_encounters,
    load_existing_ref_tokens,
    resolve_intake_path,
)
from scripts.score_clinic_constitution_survey_v1 import (  # noqa: E402
    infer_responses_from_intake,
    load_survey_bank,
    score_survey_responses,
)

POLICY_REL = Path("docs/final/artifacts/clinic_constitution_dual_lane_policy_v1.json")


def _workspace_root() -> Path:
    return _ROOT


def load_existing_lane_keys(root: Path) -> set[tuple[str, str]]:
    """(ref_token, label_lane) already in ledger."""
    from scripts.clinic_constitution_mvp_ledger_v1 import WORKSPACE_DATA_REL

    keys: set[tuple[str, str]] = set()
    clinic_dir = root / WORKSPACE_DATA_REL
    if not clinic_dir.is_dir():
        return keys
    for path in clinic_dir.glob("clinic_constitution_mvp_v1*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            enc = obj.get("encounter") or {}
            ref = enc.get("ref_token") if isinstance(enc, dict) else None
            lane = obj.get("label_lane") or "physician_gold"
            if isinstance(ref, str) and ref.strip():
                keys.add((ref.strip(), str(lane)))
    return keys


def build_consumer_capture(
    *,
    ref_token: str,
    slug: str,
    scored: dict[str, Any],
    responses: dict[str, int],
    intake_ref: str | None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    bank = load_survey_bank()
    ai = scored["ai_hypothesis"]
    return {
        "schema": "clinic_constitution_mvp_capture_v1",
        "version": "1.0.0",
        "ts_utc": now,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autobind_forbidden": True,
        "label_lane": "consumer_survey_only",
        "product_surface": "mkmlife_style_public",
        "encounter": {"ref_token": ref_token},
        "modalities_present": {
            "survey": True,
            "face_image": False,
            "voice_sample": False,
            "birth_profile": False,
        },
        "observation_proxies": scored["observation_proxies"],
        "ai_hypothesis": {
            **ai,
            "rationale_short": (
                f"[HYPO] survey pack {bank.get('pack_id')}; "
                f"answered={scored.get('survey_meta', {}).get('n_items_answered')}"
            ),
        },
        "physician_constitution": {
            "label": "withheld",
            "recorded_by_role": "licensed_km_physician",
            "notes": (
                "consumer_survey_only lane — no on-site KM physician adjudication; "
                "mkmlife/public surfaces cannot collect physician gold."
            ),
        },
        "agreement": {
            "ai_physician_match": False,
            "disagreement_code": "physician_withheld",
        },
        "survey_pack_id": bank.get("pack_id"),
        "survey_responses": responses,
        "intake_ref": intake_ref,
        "patient_facing_copy_ack": True,
        "import_meta": {
            "source": "append_clinic_consumer_survey_capture_v1",
            "slug": slug,
            "pseudo_responses_from_intake": intake_ref is not None,
        },
    }


def run_append(
    root: Path,
    *,
    dry_run: bool,
    skip_existing: bool,
    slugs: set[str] | None,
    from_registry: bool,
    ref_token: str | None,
    responses_json: str | None,
) -> dict[str, Any]:
    appended: list[str] = []
    skipped: list[dict[str, str]] = []
    errors: list[str] = []

    existing_keys = load_existing_lane_keys(root) if skip_existing else set()

    if from_registry:
        registry = json.loads((root / REGISTRY_REL).read_text(encoding="utf-8"))
        for enc in iter_clinical_encounters(registry):
            slug = str(enc.get("slug") or "")
            if slugs is not None and slug not in slugs:
                continue
            intake_path = resolve_intake_path(root, enc)
            if not intake_path or not intake_path.is_file():
                errors.append(f"{slug}: intake missing")
                continue
            intake_doc = json.loads(intake_path.read_text(encoding="utf-8"))
            ref = (intake_doc.get("encounter") or {}).get("ref_token")
            if not isinstance(ref, str) or not ref.strip():
                errors.append(f"{slug}: ref_token missing")
                continue
            ref = ref.strip()
            key = (ref, "consumer_survey_only")
            if skip_existing and key in existing_keys:
                skipped.append({"slug": slug, "ref_token": ref, "reason": "lane_exists"})
                continue
            bank = load_survey_bank(root)
            intake = intake_doc.get("intake") or {}
            responses = infer_responses_from_intake(bank, intake)
            scored = score_survey_responses(bank, responses)
            record = build_consumer_capture(
                ref_token=ref,
                slug=slug,
                scored=scored,
                responses=responses,
                intake_ref=f"reports/{slug}_intake_fusion_v1.json",
            )
            if dry_run:
                appended.append(ref)
                existing_keys.add(key)
                continue
            append_clinic_capture_line(root, record, set_ts_if_missing=False)
            appended.append(ref)
            existing_keys.add(key)
        return _report(appended, skipped, errors, dry_run)

    if not ref_token or not responses_json:
        errors.append("single capture requires --ref-token and --responses-json")
        return _report(appended, skipped, errors, dry_run)

    responses = {str(k): int(v) for k, v in json.loads(responses_json).items()}
    bank = load_survey_bank(root)
    scored = score_survey_responses(bank, responses)
    key = (ref_token.strip(), "consumer_survey_only")
    if skip_existing and key in existing_keys:
        skipped.append({"ref_token": ref_token, "reason": "lane_exists"})
        return _report(appended, skipped, errors, dry_run)

    record = build_consumer_capture(
        ref_token=ref_token.strip(),
        slug="manual",
        scored=scored,
        responses=responses,
        intake_ref=None,
    )
    if not dry_run:
        append_clinic_capture_line(root, record, set_ts_if_missing=False)
    appended.append(ref_token.strip())
    return _report(appended, skipped, errors, dry_run)


def _report(
    appended: list[str],
    skipped: list[dict[str, str]],
    errors: list[str],
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "schema": "clinic_consumer_survey_append_report_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dry_run": dry_run,
        "label_lane": "consumer_survey_only",
        "policy_ref": str(POLICY_REL).replace("\\", "/"),
        "n_appended": len(appended),
        "ref_tokens_appended": appended,
        "n_skipped": len(skipped),
        "skipped": skipped,
        "errors": errors,
        "research_only": True,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Append consumer survey clinic MVP captures")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-skip-existing", action="store_true")
    p.add_argument("--from-registry", action="store_true", help="Backfill active patients from intake")
    p.add_argument("--slug", action="append", default=[])
    p.add_argument("--ref-token", type=str, default="")
    p.add_argument("--responses-json", type=str, default="")
    p.add_argument(
        "--report-out",
        type=Path,
        default=Path("reports/clinic_consumer_survey_append_latest.json"),
    )
    args = p.parse_args(argv)
    root = _workspace_root()
    slugs = set(args.slug) if args.slug else None

    report = run_append(
        root,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip_existing,
        slugs=slugs,
        from_registry=args.from_registry,
        ref_token=args.ref_token or None,
        responses_json=args.responses_json or None,
    )

    out = root / args.report_out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
