# -*- coding: utf-8 -*-
"""Smoke: celebrity JSONL → hit-rate JSON; Yang-style metrics attached; expectations pass."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "run_myeongni_celebrity_benchmark_v1.py"
_DATASET = _ROOT / "data" / "myeongni" / "celebrity_saju_benchmark_v1.jsonl"


def test_celebrity_benchmark_exit_zero_and_yang_metrics_present():
    assert _SCRIPT.is_file(), str(_SCRIPT)
    assert _DATASET.is_file(), str(_DATASET)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_path = Path(tmp.name)
    try:
        p = subprocess.run(
            [sys.executable, str(_SCRIPT), "--dataset", str(_DATASET), "--out", str(out_path)],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert p.returncode == 0, p.stderr + p.stdout
        doc = json.loads(out_path.read_text(encoding="utf-8"))
        assert doc.get("schema") == "myeongni_celebrity_hit_rate_v1"
        rows = [r for r in doc.get("rows", []) if isinstance(r, dict)]
        with_yang = [r for r in rows if "yang_2015_style_metrics" in r]
        assert len(with_yang) >= 2, "expected commander/birth rows to carry yang_2015_style_metrics"
        gwa = next((r for r in with_yang if r.get("person_id") == "synthetic_gwaegang_day_only_v1"), None)
        assert gwa is not None
        ym = gwa["yang_2015_style_metrics"]
        buckets = ym.get("six_god_buckets_yang2015_names") or {}
        assert sum(int(buckets.get(k, 0)) for k in buckets) == 7
        # 일간 庚 vs 세 갑(재) + 세 계 branch(식상) + 일지 본기 무(인성)
        assert buckets.get("wealth") == 3
        assert buckets.get("hurting_god") == 3
        assert buckets.get("resource") == 1
        assert ym.get("day_stem_yinyang") == "yang"
        summ = doc.get("summary") or {}
        assert summ.get("expectations_passed", 0) >= 2
    finally:
        out_path.unlink(missing_ok=True)
