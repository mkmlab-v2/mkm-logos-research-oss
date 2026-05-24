from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_scope_cms_lock_false() -> None:
    spec = importlib.util.spec_from_file_location(
        "build_saving_the_news_phase1_poc_scope_v1",
        ROOT / "scripts/build_saving_the_news_phase1_poc_scope_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    doc = mod.build_scope(news_rt_contract_exists=True)
    assert doc["gates"]["cms_publish_lock_product"] is False
    assert doc["gates"]["ready_for_external_send"] is False
    assert len(doc["steps"]) >= 4
    assert doc["exit_criteria"]["promote_to_phase2"] is False
