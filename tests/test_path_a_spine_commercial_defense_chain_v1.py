from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_path_a_spine_commercial_defense_chain_v1.py"
BUILDER = ROOT / "scripts/build_path_a_spine_commercial_defense_fact_sheet_v1.py"
FACT = ROOT / "reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json"
CHAIN_OUT = ROOT / "reports/path_a_spine_commercial_defense_chain_v1_latest.json"


def test_fact_sheet_builder_schema_offline() -> None:
    r = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(FACT.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "path_a_spine_commercial_defense_fact_sheet_v1"
    p = doc["product_lane"]
    assert float(p["byte_exact_subset_parity"]) >= 1.0
    assert float(p["global_token_saving_rate"]) > 0.2
    assert "47%" in " ".join(doc["forbidden_paste_phrases"])


def test_commercial_defense_chain_smoke() -> None:
    assert CHAIN.is_file()
    r = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--skip-microgrid",
            "--skip-masked-cohort",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = json.loads(CHAIN_OUT.read_text(encoding="utf-8-sig"))
    assert out.get("chain_ok") is True
    assert out["product_kpi"]["byte_exact_subset_parity"] >= 1.0


def test_publish_chain_smoke() -> None:
    publish = ROOT / "scripts/run_path_a_commercial_defense_publish_chain_v1.py"
    r = subprocess.run(
        [sys.executable, str(publish), "--skip-defense-chain"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    gate = json.loads(
        (ROOT / "reports/kstartup_open_innovation_20460237_paste_gate_latest.json").read_text(
            encoding="utf-8-sig"
        )
    )
    assert gate.get("ok") is True
    risk = (
        ROOT / "reports/kstartup_open_innovation_20460237_paste_ready/oi_risk_defense_v1_lock.txt"
    ).read_text(encoding="utf-8")
    assert "22.29%" in risk
    assert "47" not in risk


def test_enterprise_inbound_chain_smoke() -> None:
    inbound = ROOT / "scripts/run_path_a_enterprise_inbound_chain_v1.py"
    r = subprocess.run(
        [sys.executable, str(inbound), "--skip-publish"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    api_md = (
        ROOT / "docs/final/artifacts/media_fact_sheet_compression_api_v1_latest.md"
    ).read_text(encoding="utf-8")
    assert "B2B longform spine (product lane)" in api_md
    assert "22.29%" in api_md
    manifest = json.loads(
        (
            ROOT / "docs/final/artifacts/compression_b2b_counsel_export_manifest_v1_latest.json"
        ).read_text(encoding="utf-8-sig")
    )
    paths = {f["path"] for f in manifest.get("files") or []}
    assert "reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json" in paths
    zip_meta = json.loads(
        (ROOT / "docs/final/artifacts/compression_b2b_counsel_zip_pack_v1_latest.json").read_text(
            encoding="utf-8-sig"
        )
    )
    assert zip_meta.get("ok") is True
    assert zip_meta.get("included_count", 0) >= 16
