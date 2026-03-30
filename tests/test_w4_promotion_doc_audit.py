from __future__ import annotations

import re
from pathlib import Path

from scripts.update_w4_promotion_final import main as update_w4_main


ROOT = Path(__file__).resolve().parents[1]
W4_DOC = ROOT / "docs" / "final" / "artifacts" / "W4_PROMOTION_DECISION_FINAL.md"


def test_w4_doc_includes_aux_non_gating_audit_section() -> None:
    # Regenerate first so the audit checks the canonical generated output.
    rc = update_w4_main()
    assert rc == 0
    text = W4_DOC.read_text(encoding="utf-8")

    assert "Updated at UTC:" in text
    assert "auxiliary adapter (non-gating):" in text
    assert "aux_adapter_version =" in text
    assert "top_n_aux_non_gating_present =" in text
    assert "ranking_or_gate_participation = false (metadata only)" in text

    # Ensure the ratio shape is stable (e.g., 5/5).
    m = re.search(r"top_n_aux_non_gating_present\s*=\s*(\d+/\d+)", text)
    assert m, "top_n_aux_non_gating_present ratio must be present"
