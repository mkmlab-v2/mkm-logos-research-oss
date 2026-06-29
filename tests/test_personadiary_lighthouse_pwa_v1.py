"""Tests for personadiary lighthouse PWA gate scoring."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "scripts/run_personadiary_lighthouse_pwa_v1.py"
    spec = importlib.util.spec_from_file_location("pd_lhci", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_evaluate_report_pass():
    mod = _load()
    report = {
        "categories": {
            "pwa": {"score": 0.7},
            "accessibility": {"score": 0.9},
            "performance": {"score": 0.5},
        },
        "audits": {
            "installable-manifest": {"score": 1},
            "service-worker": {"score": 1},
        },
    }
    ok, errors = mod.evaluate_report(report, pwa_min=55, a11y_min=85, perf_min=45)
    assert ok is True
    assert errors == []


def test_evaluate_report_pwa_proxy_pass():
    mod = _load()
    report = {
        "categories": {
            "accessibility": {"score": 0.83},
            "performance": {"score": 0.5},
        },
        "audits": {},
    }
    ok, errors = mod.evaluate_report(report, pwa_min=55, a11y_min=82, perf_min=45, pwa_proxy_ok=True)
    assert ok is True
    assert errors == []
