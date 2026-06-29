"""
Backfill clinic_constitution_mvp_capture_v1 rows from patient_encounter_registry + intake fusion.

B-track bootstrap only. Does not copy intake estimates into physician gold labels unless
--physician-from-intake-estimate (explicit; inflates match_rate — not default).

Schema: docs/final/schemas/clinic_constitution_mvp_capture_v1.schema.json
Registry: docs/final/artifacts/patient_encounter_registry_v1_latest.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.clinic_constitution_mvp_ledger_v1 import (  # noqa: E402
    WORKSPACE_DATA_REL,
    append_clinic_capture_line,
    validate_clinic_capture_record,
)

REGISTRY_REL = Path("docs/final/artifacts/patient_encounter_registry_v1_latest.json")
SKIP_STATUS = frozenset({"deprecated", "operator_profile", "family_anchor"})
SKIP_RAIL = frozenset({"operator", "family"})

KO_TO_CONSTITUTION: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"태음"), "taeeum"),
    (re.compile(r"소양"), "soyang"),
    (re.compile(r"태양"), "taeyang"),
    (re.compile(r"소음"), "soeum"),
]

HEAT_KW = ("열", "땀", "화", "상열", "추위 적", "홍조", "손발 뜨")
COLD_KW = ("한", "냉", "시림", "수존복냉", "추위", "따뜻하지", "오한")
DIGEST_KW = ("소화", "설사", "변비", "복부", "배", "식욕")
ACTIVITY_KW = ("기력", "피로", "활동", "근력", "무기력", "기진")
MOISTURE_KW = ("땀", "습", "건조", "갈증", "요실", "백태", "설홍")


def _workspace_root() -> Path:
    return _ROOT


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _intake_text(intake: dict[str, Any]) -> str:
    parts: list[str] = []
    syms = intake.get("symptoms")
    if isinstance(syms, list):
        parts.extend(str(s) for s in syms)
    for key in ("situation", "subjective_notes", "objective_draft"):
        v = intake.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return " ".join(parts)


def _score_keywords(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for kw in keywords if kw in text)


def observation_proxies_from_intake(intake: dict[str, Any]) -> dict[str, float]:
    text = _intake_text(intake)

    def lean(plus: int, minus: int, default: float = 0.5) -> float:
        if plus == minus == 0:
            return default
        raw = 0.5 + 0.12 * (plus - minus)
        return max(0.0, min(1.0, round(raw, 3)))

    return {
        "cold_heat_lean": lean(
            _score_keywords(text, HEAT_KW), _score_keywords(text, COLD_KW)
        ),
        "digestion_lean": lean(
            _score_keywords(text, DIGEST_KW), 0, default=0.52
        ),
        "activity_lean": lean(
            0, _score_keywords(text, ACTIVITY_KW), default=0.45
        ),
        "moisture_lean": lean(
            _score_keywords(text, MOISTURE_KW), 0, default=0.5
        ),
    }


def map_korean_sasang_label(label: str) -> tuple[str, float]:
    """Return (constitution, confidence)."""
    if not isinstance(label, str) or not label.strip():
        return "uncertain", 0.4
    s = label.strip()
    if "미입력" in s or "관찰 부족" in s or "미확정" in s:
        return "uncertain", 0.38
    for pattern, code in KO_TO_CONSTITUTION:
        if pattern.search(s):
            conf = 0.52 if "확실치 않음" in s or "추정" in s else 0.62
            return code, conf
    return "uncertain", 0.42


def resolve_intake_path(root: Path, encounter: dict[str, Any]) -> Path | None:
    pointer_rel = encounter.get("pointer")
    if isinstance(pointer_rel, str) and pointer_rel.strip():
        pointer = _load_json(root / pointer_rel)
        intake_rel = (pointer.get("paths") or {}).get("intake")
        if isinstance(intake_rel, str) and intake_rel.strip():
            return root / intake_rel
    paths = encounter.get("paths")
    if isinstance(paths, dict):
        intake_rel = paths.get("intake")
        if isinstance(intake_rel, str) and intake_rel.strip():
            return root / intake_rel
    return None


def build_capture_from_intake(
    intake_doc: dict[str, Any],
    *,
    slug: str,
    physician_from_estimate: bool,
    ts_utc: str | None = None,
) -> dict[str, Any]:
    enc = intake_doc.get("encounter") or {}
    ref_token = enc.get("ref_token")
    if not isinstance(ref_token, str) or not ref_token.strip():
        raise ValueError(f"{slug}: missing encounter.ref_token")

    intake = intake_doc.get("intake") or {}
    if not isinstance(intake, dict):
        raise ValueError(f"{slug}: intake block missing")

    est = intake.get("sasang_estimate") or {}
    est_label = est.get("label") if isinstance(est, dict) else ""
    ai_constitution, ai_conf = map_korean_sasang_label(str(est_label or ""))

    profile = intake_doc.get("profile") or {}
    has_birth = bool(
        isinstance(profile, dict)
        and isinstance(profile.get("birth_instant_utc"), str)
        and profile.get("birth_instant_utc", "").strip()
    )

    if physician_from_estimate and ai_constitution in {
        "taeeum",
        "soyang",
        "taeyang",
        "soeum",
    }:
        physician_label = ai_constitution
        physician_notes = (
            "[BACKFILL] physician label mirrored from intake sasang_estimate — "
            "replace with licensed adjudication."
        )
        disagreement_code = "none" if ai_constitution == physician_label else "modality_insufficient"
        ai_match = ai_constitution == physician_label
    else:
        physician_label = "withheld"
        physician_notes = (
            "[BACKFILL] No physician 4-label adjudication in SSOT; "
            "update physician_constitution after clinic visit."
        )
        disagreement_code = "physician_withheld"
        ai_match = False

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schema": "clinic_constitution_mvp_capture_v1",
        "version": "1.0.0",
        "ts_utc": ts_utc or now,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autobind_forbidden": True,
        "encounter": {"ref_token": ref_token.strip()},
        "modalities_present": {
            "survey": bool(_intake_text(intake)),
            "face_image": False,
            "voice_sample": False,
            "birth_profile": has_birth,
        },
        "observation_proxies": observation_proxies_from_intake(intake),
        "ai_hypothesis": {
            "constitution": ai_constitution,
            "confidence": ai_conf,
            "model_id": "patient_registry_backfill_v1",
            "rationale_short": f"[HYPO] intake sasang_estimate: {est_label}",
        },
        "physician_constitution": {
            "label": physician_label,
            "recorded_by_role": "licensed_km_physician",
            "notes": physician_notes,
        },
        "agreement": {
            "ai_physician_match": ai_match,
            "disagreement_code": disagreement_code,
        },
        "intake_ref": f"reports/{slug}_intake_fusion_v1.json",
        "patient_facing_copy_ack": True,
        "label_lane": "physician_gold",
        "product_surface": "clinic_registry_backfill",
        "import_meta": {
            "source": "patient_registry_backfill_v1",
            "slug": slug,
            "registry_schema": "patient_encounter_registry_v1",
            "physician_label_automatic": physician_from_estimate,
        },
    }


def load_existing_ref_tokens(root: Path) -> set[str]:
    clinic_dir = root / WORKSPACE_DATA_REL
    tokens: set[str] = set()
    if not clinic_dir.is_dir():
        return tokens
    for path in sorted(clinic_dir.glob("clinic_constitution_mvp_v1*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            enc = obj.get("encounter")
            if isinstance(enc, dict) and isinstance(enc.get("ref_token"), str):
                tokens.add(enc["ref_token"].strip())
    return tokens


def iter_clinical_encounters(registry: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for enc in registry.get("encounters") or []:
        if not isinstance(enc, dict):
            continue
        status = enc.get("status")
        if status in SKIP_STATUS:
            continue
        rail = enc.get("rail") or registry.get("rail_default") or "Track B"
        if rail in SKIP_RAIL:
            continue
        out.append(enc)
    return out


def run_import(
    root: Path,
    *,
    dry_run: bool,
    skip_existing: bool,
    physician_from_estimate: bool,
    slugs: set[str] | None,
) -> dict[str, Any]:
    registry_path = root / REGISTRY_REL
    registry = _load_json(registry_path)
    existing = load_existing_ref_tokens(root) if skip_existing else set()

    appended: list[str] = []
    skipped: list[dict[str, str]] = []
    errors: list[str] = []

    for enc in iter_clinical_encounters(registry):
        slug = str(enc.get("slug") or "")
        if slugs is not None and slug not in slugs:
            continue
        intake_path = resolve_intake_path(root, enc)
        if intake_path is None or not intake_path.is_file():
            errors.append(f"{slug}: intake path not found")
            continue
        try:
            intake_doc = _load_json(intake_path)
            record = build_capture_from_intake(
                intake_doc,
                slug=slug,
                physician_from_estimate=physician_from_estimate,
            )
        except (ValueError, json.JSONDecodeError) as e:
            errors.append(f"{slug}: {e}")
            continue

        ref = record["encounter"]["ref_token"]
        if skip_existing and ref in existing:
            skipped.append({"slug": slug, "ref_token": ref, "reason": "already_in_ledger"})
            continue

        errs = validate_clinic_capture_record(record)
        if errs:
            errors.append(f"{slug}: validate: {'; '.join(errs)}")
            continue

        if dry_run:
            appended.append(ref)
            existing.add(ref)
            continue

        append_clinic_capture_line(root, record, set_ts_if_missing=False)
        appended.append(ref)
        existing.add(ref)

    return {
        "schema": "clinic_mvp_registry_import_report_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "dry_run": dry_run,
        "skip_existing": skip_existing,
        "physician_from_intake_estimate": physician_from_estimate,
        "registry_path": str(REGISTRY_REL).replace("\\", "/"),
        "n_appended": len(appended),
        "ref_tokens_appended": appended,
        "n_skipped": len(skipped),
        "skipped": skipped,
        "errors": errors,
        "research_only": True,
        "not_for_track_a_promotion": True,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Import clinic MVP ledger rows from patient encounter registry (B-track)"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and validate only; do not append JSONL",
    )
    p.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Append even if ref_token already exists in ledger files",
    )
    p.add_argument(
        "--physician-from-intake-estimate",
        action="store_true",
        help="Mirror physician label from intake estimate (bootstrap only; not gold standard)",
    )
    p.add_argument(
        "--slug",
        action="append",
        default=[],
        help="Limit to slug(s); repeatable",
    )
    p.add_argument(
        "--report-out",
        type=Path,
        default=Path("reports/clinic_mvp_registry_import_latest.json"),
    )
    args = p.parse_args(argv)
    root = _workspace_root()
    slugs = set(args.slug) if args.slug else None

    report = run_import(
        root,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip_existing,
        physician_from_estimate=args.physician_from_intake_estimate,
        slugs=slugs,
    )

    out_path = root / args.report_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
