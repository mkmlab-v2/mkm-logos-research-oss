#!/usr/bin/env python3
"""P1: Golden-40 compare with lexicon function-word denylist on production 41658 ([HYPO])."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: E402
    _load_signoff_relaxed,
    _metrics,
    _run_eval,
)
from scripts.run_ultra_compression_default import INPUT_V2  # noqa: E402

PILOT = ROOT / "reports/constitution/btrack_pilot"
BASE = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
OUT = ROOT / "reports/lexicon_function_word_denylist_pilot_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not BASE.is_file() or not INPUT_V2.is_file():
        print("ABORT: missing base lexicon or bench input")
        return 1

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    relaxed, allow, exclude = _load_signoff_relaxed()

    m_default = _metrics(_run_eval(src, lexicon_path=BASE, domain_relaxed=relaxed, relaxed_case_allowlist=allow, relaxed_case_exclude=exclude))
    m_deny = _metrics(
        _run_eval(
            src,
            lexicon_path=BASE,
            domain_relaxed=relaxed,
            relaxed_case_allowlist=allow,
            relaxed_case_exclude=exclude,
            exclude_function_words=True,
        )
    )
    delta_saving = (m_deny.get("global_token_saving_rate") or 0) - (m_default.get("global_token_saving_rate") or 0)
    delta_j = (m_deny.get("avg_reconstruction_fidelity_jaccard") or 0) - (
        m_default.get("avg_reconstruction_fidelity_jaccard") or 0
    )

    doc = {
        "schema": "lexicon_function_word_denylist_pilot_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "lexicon_path": str(BASE.relative_to(ROOT)).replace("\\", "/"),
        "golden40_compare": {
            "default_bridge": m_default,
            "exclude_function_words": m_deny,
            "delta": {
                "global_token_saving_rate": delta_saving,
                "avg_reconstruction_fidelity_jaccard": delta_j,
            },
        },
        "verdict": {
            "denylist_improves_saving": delta_saving > 0,
            "denylist_harms_jaccard_over_2pp": delta_j < -0.02,
            "recommendation": "",
        },
    }
    if delta_saving > 0 and delta_j >= -0.02:
        doc["verdict"]["recommendation"] = (
            "Opt-in exclude_function_words on research eval paths; keep Track A frozen profile unchanged until human Track A sign-off."
        )
    elif delta_saving <= 0:
        doc["verdict"]["recommendation"] = "Denylist neutral or negative on saving — keep opt-in off for promotion claims."
    else:
        doc["verdict"]["recommendation"] = "Saving up but Jaccard drop > 2pp — tune denylist or case scope before wider use."

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "delta_saving_pp": round(delta_saving * 100, 2),
                "delta_j_pp": round(delta_j * 100, 2),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
