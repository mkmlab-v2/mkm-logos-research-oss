"""OI 20460237 paste must not reuse OpenData 327 / Startup Package 340 copy."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _load_build_module():
    path = SCRIPTS / "build_kstartup_open_innovation_20460237_paste_ready_v1.py"
    spec = importlib.util.spec_from_file_location("oi_paste_build", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_oi_paste_not_policy_fund_rag():
    mod = _load_build_module()
    fields = mod.build_fields()
    primary = (
        fields["step4_tsksNm.txt"]
        + fields["step4_tsksCtnt.txt"]
        + fields["step2_majrProd.txt"]
    )
    assert "정책자금" not in primary
    assert "한국평가데이터" in fields["step4_tsksCtnt.txt"]
    assert "RPA" in fields["step4_tsksNm.txt"] or "RPA" in fields["step2_majrProd.txt"]


def test_oi_paste_gate_exit_zero():
    gate = SCRIPTS / "check_kstartup_open_innovation_20460237_paste_gate_v1.py"
    spec = importlib.util.spec_from_file_location("oi_paste_gate", gate)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(mod)
    ok, errors, _meta = mod.verify_paste_pack(ROOT)
    assert ok, errors
