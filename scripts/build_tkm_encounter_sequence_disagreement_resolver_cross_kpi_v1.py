#!/usr/bin/env python3
"""Build TKM disagreement × conflict resolver cross KPI [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1_latest.json"
DRAFTS = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_draft_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_mod(rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build() -> dict[str, Any]:
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    logos_mod = _load_mod("scripts/tkm_encounter_sequence_logos_sidecar_v1.py")
    clf_mod = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")
    drafts = _load(DRAFTS)

    records = logos_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    disagreement_count = 0
    disagreement_resolver_wired = 0
    disagreement_with_lens_conflict = 0
    physician_authority_preserved = 0
    curated_pointer_count = 0
    disagreement_codes: dict[str, int] = {}
    resolver_by_disagreement: dict[str, int] = {}

    for row in records:
        if clf_mod.is_dummy_encounter_sequence(row):
            continue
        physician = row.get("physician_closure") if isinstance(row.get("physician_closure"), dict) else {}
        agr = physician.get("agreement") if isinstance(physician.get("agreement"), dict) else {}
        if agr.get("ai_physician_match") is not False:
            continue
        disagreement_count += 1
        code = str(agr.get("disagreement_code") or "unknown")
        disagreement_codes[code] = disagreement_codes.get(code, 0) + 1
        curated = row.get("curated_learning_pointer")
        if isinstance(curated, dict) and curated.get("disagreement_recorded") is True:
            curated_pointer_count += 1
        resolver = row.get("l7_conflict_resolver_ref")
        if not isinstance(resolver, dict):
            continue
        disagreement_resolver_wired += 1
        status = str(resolver.get("resolver_status") or "unknown")
        resolver_by_disagreement[status] = resolver_by_disagreement.get(status, 0) + 1
        if status in ("advisory_partial", "advisory_mismatch"):
            disagreement_with_lens_conflict += 1
        if resolver.get("final_action_observed") == "physician_authority_preserved":
            physician_authority_preserved += 1

    cross_rate = (
        round(disagreement_with_lens_conflict / disagreement_resolver_wired, 4)
        if disagreement_resolver_wired
        else None
    )
    authority_rate = (
        round(physician_authority_preserved / disagreement_resolver_wired, 4)
        if disagreement_resolver_wired
        else None
    )
    kpi_ok = (
        disagreement_count >= 1
        and disagreement_resolver_wired >= 1
        and curated_pointer_count >= 1
        and drafts.get("draft_ok") is True
        and int(drafts.get("disagreement_draft_count") or 0) >= 1
    )

    return {
        "schema": "tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "kpi_ok": kpi_ok,
        "disagreement_count": disagreement_count,
        "disagreement_resolver_wired_count": disagreement_resolver_wired,
        "disagreement_with_lens_conflict_count": disagreement_with_lens_conflict,
        "physician_authority_preserved_count": physician_authority_preserved,
        "curated_learning_pointer_count": curated_pointer_count,
        "disagreement_code_counts": disagreement_codes,
        "resolver_status_on_disagreement_counts": resolver_by_disagreement,
        "disagreement_lens_conflict_cross_rate": cross_rate,
        "disagreement_physician_authority_rate": authority_rate,
        "curated_draft_count": drafts.get("disagreement_draft_count"),
        "note_ko": "불일치×resolver 교차 [HYPO][NON_GATING]; human-curated path만; auto-training·Track A 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("kpi_ok"), "disagreement": doc.get("disagreement_count")}))
    return 0 if doc.get("kpi_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
