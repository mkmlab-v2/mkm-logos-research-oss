#!/usr/bin/env python3
"""3a pilot: 41658 lexicon + only_in_41775 entries for six-case delta forms; re-bench Golden 40."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: E402
    _load_signoff_relaxed,
    _metrics,
    _run_eval,
)
from scripts.run_ultra_compression_default import INPUT_V2  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
FEAS = PILOT / "master_codebook_other_align_feasibility_v1.json"
DIFF = PILOT / "master_codebook_41775_vs_41658_atom_diff_v1.json"
P658 = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
P775 = PILOT / "master_codebook_lexicon_v1_41775_rows_archived_20260523.json"
DEFAULT_OVERLAY = PILOT / "master_codebook_lexicon_v1_41658_3a_pilot_overlay.json"
DEFAULT_OUT = PILOT / "master_codebook_3a_overlay_pilot_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atom_form(atom_id: str) -> str:
    return atom_id.split("::", 1)[1].lower() if "::" in atom_id else atom_id.lower()


def _build_overlay(
    base_path: Path,
    archived_path: Path,
    forms_to_add: set[str],
    out_path: Path,
) -> dict[str, Any]:
    base = json.loads(base_path.read_text(encoding="utf-8"))
    arch = json.loads(archived_path.read_text(encoding="utf-8"))
    by_id = {e["atom_id"]: e for e in base.get("entries") or [] if isinstance(e, dict) and e.get("atom_id")}
    arch_by_id = {
        e["atom_id"]: e for e in arch.get("entries") or [] if isinstance(e, dict) and e.get("atom_id")
    }
    added: list[str] = []
    for aid, ent in arch_by_id.items():
        if _atom_form(aid) not in forms_to_add:
            continue
        if aid in by_id:
            continue
        by_id[aid] = ent
        added.append(aid)
    entries = list(by_id.values())
    payload = dict(base)
    payload["generated_at_utc"] = _utc()
    payload["row_count"] = len(entries)
    payload["entries"] = entries
    payload["overlay_meta"] = {
        "schema": "master_codebook_3a_pilot_overlay_v1",
        "base": str(base_path.name),
        "archived_source": str(archived_path.name),
        "forms_requested": sorted(forms_to_add),
        "atom_ids_added": added,
        "atom_ids_added_count": len(added),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return payload["overlay_meta"]


def main() -> int:
    ap = argparse.ArgumentParser(description="3a overlay pilot Golden 40")
    ap.add_argument("--overlay-out", type=Path, default=DEFAULT_OVERLAY)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    for p in (FEAS, DIFF, P658, P775, INPUT_V2):
        if not p.is_file():
            print(f"ERROR: missing {p}", file=sys.stderr)
            return 2

    feas = json.loads(FEAS.read_text(encoding="utf-8"))
    forms: set[str] = set()
    for row in feas.get("per_delta_case") or []:
        for f in row.get("only_in_41775_forms_in_case_text") or []:
            forms.add(str(f).lower())

    overlay_path = args.overlay_out if args.overlay_out.is_absolute() else ROOT / args.overlay_out
    meta = _build_overlay(P658, P775, forms, overlay_path)

    src_doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    domain_relaxed, allowlist, exclude = _load_signoff_relaxed()

    m_base = _metrics(
        _run_eval(
            src_doc,
            lexicon_path=P658,
            domain_relaxed=domain_relaxed,
            relaxed_case_allowlist=allowlist,
            relaxed_case_exclude=exclude,
        )
    )
    m_overlay = _metrics(
        _run_eval(
            src_doc,
            lexicon_path=overlay_path,
            domain_relaxed=domain_relaxed,
            relaxed_case_allowlist=allowlist,
            relaxed_case_exclude=exclude,
        )
    )
    m775 = _metrics(
        _run_eval(
            src_doc,
            lexicon_path=P775,
            domain_relaxed=domain_relaxed,
            relaxed_case_allowlist=allowlist,
            relaxed_case_exclude=exclude,
        )
    )

    frozen_saving = 0.47538677918424754
    frozen_jaccard = 0.8904921794966301

    doc: dict[str, Any] = {
        "schema": "master_codebook_3a_overlay_pilot_v1",
        "verified_at_utc": _utc(),
        "overlay_lexicon": str(overlay_path.resolve()),
        "overlay_meta": meta,
        "metrics_41658_base": m_base,
        "metrics_41658_3a_overlay": m_overlay,
        "metrics_41775_archived": m775,
        "delta_overlay_minus_base": {
            "global_token_saving_rate": round(
                float(m_overlay["global_token_saving_rate"] or 0)
                - float(m_base["global_token_saving_rate"] or 0),
                6,
            ),
            "avg_reconstruction_fidelity_jaccard": round(
                float(m_overlay["avg_reconstruction_fidelity_jaccard"] or 0)
                - float(m_base["avg_reconstruction_fidelity_jaccard"] or 0),
                6,
            ),
        },
        "delta_overlay_minus_41775": {
            "global_token_saving_rate": round(
                float(m_overlay["global_token_saving_rate"] or 0)
                - float(m775["global_token_saving_rate"] or 0),
                6,
            ),
            "avg_reconstruction_fidelity_jaccard": round(
                float(m_overlay["avg_reconstruction_fidelity_jaccard"] or 0)
                - float(m775["avg_reconstruction_fidelity_jaccard"] or 0),
                6,
            ),
        },
        "frozen_headline_41775": {
            "global_token_saving_rate": frozen_saving,
            "avg_reconstruction_fidelity_jaccard": frozen_jaccard,
        },
        "jaccard_0_89_recovered_by_overlay": float(m_overlay["avg_reconstruction_fidelity_jaccard"] or 0)
        >= frozen_jaccard - 1e-6,
        "verdict": "confirm_needed",
    }

    dj = doc["delta_overlay_minus_41775"]["avg_reconstruction_fidelity_jaccard"]
    if abs(dj) < 1e-6 and abs(doc["delta_overlay_minus_41775"]["global_token_saving_rate"]) < 1e-6:
        doc["verdict"] = "3a_overlay_restores_41775_kpi"
    elif doc["jaccard_0_89_recovered_by_overlay"]:
        doc["verdict"] = "3a_overlay_meets_or_exceeds_frozen_jaccard"
    elif float(m_overlay["avg_reconstruction_fidelity_jaccard"] or 0) > float(
        m_base["avg_reconstruction_fidelity_jaccard"] or 0
    ):
        doc["verdict"] = "3a_partial_jaccard_lift_insufficient_for_089"
    else:
        doc["verdict"] = "3a_no_material_lift"

    out = args.report_out if args.report_out.is_absolute() else ROOT / args.report_out
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {out}")
    print(f"verdict={doc['verdict']}")
    print(f"overlay added {meta['atom_ids_added_count']} atom_ids")
    print(f"41658 base jaccard={m_base['avg_reconstruction_fidelity_jaccard']}")
    print(f"3a overlay jaccard={m_overlay['avg_reconstruction_fidelity_jaccard']}")
    print(f"41775 archived jaccard={m775['avg_reconstruction_fidelity_jaccard']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
