from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = ROOT / "scripts" / "run_myeongri_deterministic_lora_inference_eval_v1.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("myeongri_deterministic_lora_inf_v1", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_extract_json_balanced_prefix_with_trailing_garbage() -> None:
    mod = _load_script()
    good = {"schema": "saju_global_birth_result_v1", "version": "1.0.0"}
    blob = json.dumps(good, ensure_ascii=False) + '{"broken":'
    assert mod._extract_json_object(blob) == good


def test_extract_json_double_encoded_string() -> None:
    mod = _load_script()
    inner = {"schema": "saju_global_birth_result_v1", "k": 1}
    wrapped = json.dumps(json.dumps(inner, ensure_ascii=False), ensure_ascii=False)
    assert mod._extract_json_object(wrapped) == inner
