from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_registry_manifest() -> None:
    from scripts.mkm_unified_asset_registry_v1 import (  # noqa: WPS433
        build_registry_manifest,
        resolve_lane,
    )

    doc = build_registry_manifest(out_path=ROOT / "docs/final/artifacts/mkm_unified_asset_registry_v1_latest.json")
    assert doc["schema"] == "mkm_unified_asset_registry_v1"
    assert "corpus_core_31k" in doc["lane_keys"]
    assert "manuscript_fabric_v2" in doc["lane_keys"]
    assert "decoy_experience_layer" in doc["lane_keys"]
    corpus = resolve_lane("corpus_core_31k")
    keys = {p.key for p in corpus.paths}
    assert "corpus_array" in keys
    assert "corpus_manifest" in keys
    assert corpus.lazy_load is True


def test_corpus_resolve_does_not_require_lexicon_file() -> None:
    from scripts.mkm_unified_asset_registry_v1 import assert_lane_isolation, resolve_lane  # noqa: WPS433

    res = resolve_lane("corpus_core_31k")
    assert_lane_isolation("corpus_core_31k")
    assert all(p.key != "lexicon_rows" for p in res.paths)


def test_cli_build_exit() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/mkm_unified_asset_registry_v1.py"), "build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["ok"] is True


def test_cli_resolve_corpus() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/mkm_unified_asset_registry_v1.py"),
            "resolve",
            "--lane",
            "corpus_core_31k",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["lane_key"] == "corpus_core_31k"
    assert doc["lazy_load"] is True
