"""Smoke: Sasang NL RAG excerpt builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_notebooklm_lens_sasang_rag_excerpt_smoke() -> None:
    script = ROOT / "scripts" / "build_notebooklm_lens_sasang_rag_excerpt_v1.py"
    out = ROOT / "docs" / "final" / "artifacts" / "notebooklm_lens_sasang_rag_excerpt_v1.md"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "[HYPO]" in text
    assert "금화교역" in text
    assert "IJEOMA_BTRACK" in text
    assert "Core framing" in text
    assert "火剋金" in text
    assert "金器" in text
    assert "containment" in text
    assert "기상역상" in text
    assert "SECONDARY_PROXY" in text


def test_lens_sasang_pack_has_expanded_allowlist() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_notebooklm_lens_source_packs_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    idx = ROOT / "reports" / "notebooklm_lens_packs_v1" / "index.json"
    doc = json.loads(idx.read_text(encoding="utf-8"))
    files = doc.get("packs", {}).get("LENS_SASANG", {}).get("files", [])
    copied = [f for f in files if f.get("status") == "copied"]
    assert len(copied) >= 8, copied


def test_ijoeoma_btrack_pack_includes_secondary_proxy() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_notebooklm_lens_source_packs_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    idx = ROOT / "reports" / "notebooklm_lens_packs_v1" / "index.json"
    doc = json.loads(idx.read_text(encoding="utf-8"))
    files = doc.get("packs", {}).get("IJEOMA_BTRACK", {}).get("files", [])
    copied_paths = {f.get("rel") for f in files if f.get("status") == "copied"}
    assert "docs/research/raw/IJEOMA_SECONDARY_PROXY_v1.json" in copied_paths
    assert "docs/research/IJEOMA_SECONDARY_PROXY_LIT_REVIEW_2026-06-26.md" in copied_paths


def test_ijoeoma_btrack_pack_includes_physical_proxy_index() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_notebooklm_lens_source_packs_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    idx = ROOT / "reports" / "notebooklm_lens_packs_v1" / "index.json"
    doc = json.loads(idx.read_text(encoding="utf-8"))
    files = doc.get("packs", {}).get("IJEOMA_BTRACK", {}).get("files", [])
    copied_paths = {f.get("rel") for f in files if f.get("status") == "copied"}
    assert "reports/constitution/btrack_pilot/cheonyucho_physical_proxy_index_v1_latest.json" in copied_paths
    assert "docs/research/raw/CHEONYUCHO_PHYSICAL_PARK1985_NLK_reply_2026_nl_proxy.md" in copied_paths
