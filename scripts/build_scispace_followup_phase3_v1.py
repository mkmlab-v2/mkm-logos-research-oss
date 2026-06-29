#!/usr/bin/env python3
"""Phase-3: SCAT NL proxy upload, 천유초 草/抄 verify JSON, ARC↔control-integrity grep."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_UUID = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"
SCAT_BENCH = ROOT / "reports/constitution/btrack_pilot/sasang_scat_voice_face_bench_v1.json"
SCAT_PROXY = ROOT / "docs/research/raw/SASANG_SCAT_TOP3_NL_PROXY_2026-06-24.md"
RISS_PYEONRAM = ROOT / "reports/constitution/btrack_pilot/riss_sasang_clinical_pyeonram_2026-06-24.json"
P344_MANIFEST = ROOT / "data/corpus/ijeoma/_inventory/cheonyucho_p344_partial_ingest_v1.json"
LEE_GREP = ROOT / "reports/constitution/btrack_pilot/lee2005_pdf_grep_cheonyucho_v1.json"
MKM_PROFILES = ROOT / "docs/final/artifacts/mkm_control_integrity_lora_model_profiles_v1.json"
ARC_POINTER = ROOT / "reports/constitution/btrack_pilot/arc_architects_ttt_lora_pointer_v1.json"
OUT_GRASS = ROOT / "reports/constitution/btrack_pilot/cheonyucho_grass_vs_chao_verify_v1.json"
OUT_ARC_GREP = ROOT / "reports/constitution/btrack_pilot/arc_mkm_control_integrity_grep_v1.json"
OUT_MANIFEST = ROOT / "reports/constitution/btrack_pilot/scispace_followup_phase3_manifest_v1.json"
ARC_REPO = "https://github.com/da-fr/arc-prize-2024.git"
ARC_SHALLOW = ROOT / "reports/constitution/btrack_pilot/_arc_prize_2024_shallow"
PROXY_TITLE = "[PAPER_PROXY] SASANG_SCAT_TOP3_2026-06-24"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _notebook_source_count() -> int:
    proc = subprocess.run(
        ["nlm", "notebook", "get", NOTEBOOK_UUID, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        return 300
    val = _load_json_stdout(proc.stdout)
    return len(val.get("sources") or [])


def _load_json_stdout(raw: str) -> dict[str, Any]:
    return json.loads(raw)


def _source_titles() -> set[str]:
    proc = subprocess.run(
        ["nlm", "notebook", "get", NOTEBOOK_UUID, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        return set()
    val = _load_json_stdout(proc.stdout)
    return {s.get("title", "") for s in val.get("sources") or []}


def build_scat_proxy_md() -> str:
    bench = _load(SCAT_BENCH)
    lines = [
        "# [PAPER_PROXY] SCAT · voice/face constitution bench (Top-3 + headline)",
        "",
        "**Track:** B · `[PAPER_PROXY]` · `send_gate: HOLD` · `research_only`",
        f"**Generated:** {_utc()}",
        f"**Upstream:** `{SCAT_BENCH.relative_to(ROOT).as_posix()}`",
        "",
        "## Headline (SciSpace export — verify primary)",
        "",
        f"- {bench.get('headline', {}).get('scat_expert_agreement_note', '')}",
        f"- Caveat: {bench.get('headline', {}).get('caveat', '')}",
        "",
        "## Top-3 papers (bibliographic enriched)",
        "",
    ]
    top_keys = (
        "Comparison between Diagnostic Results of the Sasang Constitutional Analysis Tool",
        "Development of an integrated Sasang constitution diagnosis method",
        "The Concordance and Validity Assessment of Diagnosis for the Expert",
    )
    n = 0
    for entry in bench.get("entries", []):
        title = entry.get("title", "")
        if not any(title.startswith(k) or k in title for k in top_keys):
            continue
        if "The Concordance" in title and title.endswith("for the"):
            continue  # skip truncated duplicate
        n += 1
        bib = entry.get("bibliographic") or {}
        lines.extend(
            [
                f"### {n}. {title}",
                "",
                f"- Authors: {entry.get('authors', '')}",
                f"- Modality: {entry.get('modality', '')}",
                f"- DOI: {bib.get('doi', 'n/a')} · {bib.get('doi_url', '')}",
                f"- KCI: {bib.get('kci_url', 'n/a')}",
                f"- Results excerpt: {entry.get('results_excerpt', '')[:600]}",
                f"- Limitations: {entry.get('limitations_excerpt', '')[:400]}",
                "",
            ]
        )
        if n >= 3:
            break
    lines.append("---")
    lines.append("Not clinical prescription. Not Track A KPI. Hanja canon not from this proxy alone.")
    return "\n".join(lines) + "\n"


def upload_scat_proxy(skip_upload: bool) -> dict[str, Any]:
    text = build_scat_proxy_md()
    SCAT_PROXY.parent.mkdir(parents=True, exist_ok=True)
    SCAT_PROXY.write_text(text, encoding="utf-8")
    row: dict[str, Any] = {
        "proxy_path": str(SCAT_PROXY.relative_to(ROOT)).replace("\\", "/"),
        "title": PROXY_TITLE,
        "chars": len(text),
        "skipped": skip_upload,
    }
    if skip_upload:
        row["ok"] = True
        row["note"] = "dry-run — proxy written only"
        return row
    if PROXY_TITLE in _source_titles():
        row["ok"] = True
        row["note"] = "already_present"
        return row
    count = _notebook_source_count()
    if count >= 300:
        row["ok"] = False
        row["error"] = f"cap_reached sources={count}"
        return row
    cmd = ["nlm", "source", "add", NOTEBOOK_UUID, "--text", text, "--title", PROXY_TITLE, "--wait"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    out = (proc.stdout or "") + (proc.stderr or "")
    row["ok"] = proc.returncode == 0 and "Added source" in out
    row["source_count_before"] = count
    row["tail"] = out[-200:]
    time.sleep(2)
    return row


def build_grass_vs_chao_verify() -> dict[str, Any]:
    riss = _load(RISS_PYEONRAM) if RISS_PYEONRAM.is_file() else {}
    lee = _load(LEE_GREP) if LEE_GREP.is_file() else {}
    lee_hits = lee.get("hanja_hits") or lee.get("matches") or {}
    p344 = _load(P344_MANIFEST) if P344_MANIFEST.is_file() else None
    p344_path = ROOT / (p344 or {}).get("disk_path", "") if p344 else None
    p344_text = ""
    if p344_path and p344_path.is_file():
        p344_text = p344_path.read_text(encoding="utf-8", errors="replace")
    p344_has_chao = "闡幽抄" in p344_text
    p344_has_grass = "闡幽草" in p344_text
    verdict = "UNVERIFIED"
    verdict_note = (
        "RISS TOC lists 第十篇. 闡幽草 p.344 (草). MKM SSOT is 闡幽抄 (抄). "
        "Lee 2005 PDF grep confirms 闡幽抄 in bibliography list only — not p.344 body. "
        "P1 target: vol.2 ISBN 9788992971706 (p.344 plausible); vol.1 ~217pp makes p.344 impossible [HYPO]."
    )
    if p344 and p344_has_chao:
        verdict_note += (
            " User paste (PARTIAL_INGEST) includes 闡幽抄"
            + (" and 闡幽草 mention" if p344_has_grass else "")
            + " — physical_verified false until scan_sha256 or library photo anchor."
        )
    doc = {
        "schema": "cheonyucho_grass_vs_chao_verify_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "research_only": True,
        "ssot_hanja": "闡幽抄",
        "toc_hanja_observed": "闡幽草",
        "verdict": verdict,
        "verdict_note": verdict_note,
        "volume_page_hypothesis": {
            "status": "external_hypo_unverified",
            "vol1": {"isbn": "9788992971690", "pages_approx": 217, "p344_possible": False},
            "vol2": {
                "isbn": "9788992971706",
                "title_guess": "사상체질과 임상편람 2 - 사상의학 문헌집",
                "pages_approx": 477,
                "p344_plausible": True,
                "riss_control_no": "8774e49918c01006ffe0bdc3ef48d419",
            },
            "note": "Page counts from bookstore metadata [HYPO] — photograph vol.2 p.344 for 草/抄",
        },
        "evidence": {
            "riss_monograph": {
                "title": riss.get("title"),
                "isbn_candidates": riss.get("isbn_candidates"),
                "toc_entry": (riss.get("toc_cheonyu_related") or [None])[0],
                "hanja_note": riss.get("hanja_note"),
            },
            "lee2005_pdf_grep": {
                "path": str(LEE_GREP.relative_to(ROOT)).replace("\\", "/") if LEE_GREP.is_file() else None,
                "闡幽抄": bool(lee_hits.get("闡幽抄") or "闡幽抄" in json.dumps(lee, ensure_ascii=False)),
                "闡幽草": bool(lee_hits.get("闡幽草") or "闡幽草" in json.dumps(lee, ensure_ascii=False)),
            },
            "p344_partial_ingest": {
                "manifest": str(P344_MANIFEST.relative_to(ROOT)).replace("\\", "/") if p344 else None,
                "disk_path": (p344 or {}).get("disk_path"),
                "闡幽抄_in_paste": p344_has_chao,
                "闡幽草_in_paste": p344_has_grass,
                "physical_verified": False,
                "layer": (p344 or {}).get("layer"),
            }
            if p344
            else None,
        },
        "human_p1_actions": [
            "P1 원전: 장서각/NLK 闡幽抄(천유초) 전문·필사·활자",
            "P2: 박석언(朴奭彦) 1985 NLK 199.1-이617ㄱ — 색인 闡幽抄",
            "P3 (선택): 사상체질과 임상편람 2 ISBN 9788992971706 p.344 — 2권 열람 시만",
            "실물 앵커: py scripts/bind_cheonyucho_physical_anchor_v1.py --scan <file> --isbn ... --call-no ...",
        ],
        "reproduce": "py scripts/build_scispace_followup_phase3_v1.py",
    }
    OUT_GRASS.parent.mkdir(parents=True, exist_ok=True)
    OUT_GRASS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def _shallow_clone_arc() -> Path | None:
    if ARC_SHALLOW.is_dir() and (ARC_SHALLOW / ".git").is_dir():
        subprocess.run(["git", "fetch", "--depth", "1", "origin"], cwd=str(ARC_SHALLOW), capture_output=True)
        subprocess.run(["git", "checkout", "main"], cwd=str(ARC_SHALLOW), capture_output=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=str(ARC_SHALLOW), capture_output=True)
        return ARC_SHALLOW
    if ARC_SHALLOW.exists():
        shutil.rmtree(ARC_SHALLOW, ignore_errors=True)
    proc = subprocess.run(
        ["git", "clone", "--depth", "1", ARC_REPO, str(ARC_SHALLOW)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        return None
    return ARC_SHALLOW


def _grep_repo(repo: Path, patterns: dict[str, str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    py_files = list(repo.rglob("*.py"))[:200]
    for label, pat in patterns.items():
        rx = re.compile(pat, re.IGNORECASE)
        found: list[str] = []
        for fp in py_files:
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if rx.search(text):
                found.append(str(fp.relative_to(repo)).replace("\\", "/"))
        hits[label] = found[:15]
    return hits


def build_arc_grep(skip_clone: bool) -> dict[str, Any]:
    pointer = _load(ARC_POINTER) if ARC_POINTER.is_file() else {}
    mkm = _load(MKM_PROFILES) if MKM_PROFILES.is_file() else {}
    mkm_lora = {
        k: {"lora_r": v.get("lora_r"), "lora_alpha": v.get("lora_alpha"), "role": v.get("role")}
        for k, v in (mkm.get("profiles") or {}).items()
    }
    arc_patterns = {
        "lora_rank_256": r"r\s*=\s*256|rank\s*=\s*256|lora.*256",
        "lora_rank_64": r"r\s*=\s*64|rank\s*=\s*64",
        "unsloth": r"unsloth|FastLanguageModel",
        "bnb_4bit": r"load_in_4bit|bnb_4bit|BitsAndBytes",
        "test_time_train": r"test.?time|TTT|train_at_test",
    }
    repo_hits: dict[str, list[str]] = {}
    clone_ok = False
    if not skip_clone:
        repo = _shallow_clone_arc()
        clone_ok = repo is not None
        if repo:
            repo_hits = _grep_repo(repo, arc_patterns)
    doc = {
        "schema": "arc_mkm_control_integrity_grep_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "research_only": True,
        "arc_pointer": str(ARC_POINTER.relative_to(ROOT)).replace("\\", "/"),
        "arc_repo": pointer.get("primary_repo", ARC_REPO),
        "clone_ok": clone_ok,
        "clone_path": str(ARC_SHALLOW.relative_to(ROOT)).replace("\\", "/") if clone_ok else None,
        "arc_grep_hits": repo_hits,
        "arc_techniques_from_pointer": pointer.get("techniques", []),
        "mkm_control_integrity_lora_profiles": mkm_lora,
        "pattern_delta_note": (
            "ARC Architects uses rank 256/64 + unsloth + 4bit (competition scale); "
            "MKM control-integrity defaults lora_r=16 alpha=16–32 for Golden Set smoke/promotion — "
            "same family (LoRA+4bit), different rank budget and eval gate (golden holdout vs ARC task)."
        ),
        "mkm_entry_scripts": [
            "scripts/Run-MkmControlIntegrityTrainInferEval.ps1",
            "scripts/check_mkm_control_integrity_promotion_gate_v1.py",
        ],
        "reproduce": "py scripts/build_scispace_followup_phase3_v1.py",
    }
    OUT_ARC_GREP.parent.mkdir(parents=True, exist_ok=True)
    OUT_ARC_GREP.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-upload", action="store_true")
    ap.add_argument("--skip-clone", action="store_true")
    args = ap.parse_args()

    upload_row = upload_scat_proxy(args.skip_upload)
    grass_doc = build_grass_vs_chao_verify()
    arc_doc = build_arc_grep(args.skip_clone)

    gate_proc = subprocess.run(
        ["py", str(ROOT / "scripts" / "check_cheonyucho_acquisition_gate_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )

    manifest = {
        "schema": "scispace_followup_phase3_manifest_v1",
        "generated_at_utc": _utc(),
        "scat_nl_upload": upload_row,
        "cheonyucho_grass_vs_chao": {
            "path": str(OUT_GRASS.relative_to(ROOT)).replace("\\", "/"),
            "verdict": grass_doc.get("verdict"),
        },
        "arc_grep": {
            "path": str(OUT_ARC_GREP.relative_to(ROOT)).replace("\\", "/"),
            "clone_ok": arc_doc.get("clone_ok"),
            "hit_counts": {k: len(v) for k, v in (arc_doc.get("arc_grep_hits") or {}).items()},
        },
        "cheonyucho_gate_exit_code": gate_proc.returncode,
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(OUT_MANIFEST), "upload": upload_row.get("ok")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
