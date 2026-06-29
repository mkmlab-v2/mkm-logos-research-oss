"""DeepNSM shadow explication + remapped crosswalk audit (B-track)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "scripts/deepnsm_shadow_explication_lib_v1.py"
CHAIN = REPO / "scripts/run_deepnsm_shadow_explication_chain_v1.py"
DISTORTION_CHAIN = REPO / "scripts/run_deepnsm_shadow_distortion_chain_v1.py"
FIXTURE = REPO / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"
GEMATRIA = REPO / "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1.jsonl"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)


def _load_lib():
    spec = importlib.util.spec_from_file_location("deepnsm_shadow_explication_lib_v1", LIB)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_normalize_latin_translit_macrons():
    lib = _load_lib()
    assert lib.normalize_latin_translit("e.lo.him") == "elohim"
    assert lib.normalize_latin_translit("egō") == "ego"
    assert lib.normalize_latin_translit("legō") == "lego"


def test_normalize_script_form_strips_accents():
    lib = _load_lib()
    assert lib.normalize_script_form("θεός") == "θεος"
    assert lib.normalize_script_form("ἐγώ") == "εγω"


@pytest.mark.skipif(not GEMATRIA.is_file(), reason="gematria lexicon missing")
def test_resolve_theos_and_su():
    lib = _load_lib()
    rows = lib.load_gematria_rows(str(GEMATRIA.resolve()))
    index = lib.build_translit_index(rows)
    theos = lib.resolve_probe_via_gematria("theos", "greek", index, rows, en_hint="god")
    assert theos["lemma_norm"] == "θεος"
    assert theos["strongs"] == "G2316"
    su = lib.resolve_probe_via_gematria("su", "greek", index, rows, en_hint="you")
    assert su["lemma_norm"] == "συ"
    assert su["strongs"] == "G4771"


@pytest.mark.skipif(not FIXTURE.is_file(), reason="500 fixture missing")
def test_explication_chain_smoke(tmp_path: Path):
    sidecar = tmp_path / "sidecar.jsonl"
    report = tmp_path / "report.json"
    r = _run(
        [
            sys.executable,
            str(CHAIN),
            "--fixture",
            str(FIXTURE),
            "--out",
            str(sidecar),
            "--report",
            str(report),
        ]
    )
    assert r.returncode == 0, r.stderr
    lines = [ln for ln in sidecar.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 500
    first = json.loads(lines[0])
    assert first["schema"] == "deepnsm_shadow_explication_v1"
    assert "resolved_probes" in first


@pytest.mark.skipif(not FIXTURE.is_file(), reason="500 fixture missing")
def test_shadow_audit_improves_or_matches_raw(tmp_path: Path):
    sidecar = tmp_path / "sidecar.jsonl"
    raw_out = tmp_path / "raw_audit.json"
    shadow_out = tmp_path / "shadow_audit.json"
    r0 = _run([sys.executable, str(CHAIN), "--fixture", str(FIXTURE), "--out", str(sidecar)])
    assert r0.returncode == 0, r0.stderr
    r1 = _run(
        [
            sys.executable,
            "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py",
            "--fixture",
            str(FIXTURE),
            "--expected-pairs",
            "500",
            "--out",
            str(raw_out),
        ]
    )
    assert r1.returncode in (0, 1)
    r2 = _run(
        [
            sys.executable,
            "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py",
            "--fixture",
            str(FIXTURE),
            "--expected-pairs",
            "500",
            "--explication-sidecar",
            str(sidecar),
            "--out",
            str(shadow_out),
        ]
    )
    assert r2.returncode in (0, 1)
    raw = json.loads(raw_out.read_text(encoding="utf-8"))["baseline"]
    shadow = json.loads(shadow_out.read_text(encoding="utf-8"))["baseline"]
    assert shadow["english_only_distortion_rate"] <= raw["english_only_distortion_rate"]
    assert shadow["prime_hit_rate"] >= raw["prime_hit_rate"]


def test_distortion_chain_script_exists():
    assert DISTORTION_CHAIN.is_file()
