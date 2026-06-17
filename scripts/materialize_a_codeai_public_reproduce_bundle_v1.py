#!/usr/bin/env python3
"""Materialize slim a-codeai public reproduce export (whitelist + leak gate + CI stub)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DEFAULT = ROOT / "docs/final/artifacts/a_codeai_public_reproduce_export_manifest_v1.json"
OUT_DIR_DEFAULT = ROOT / "exports/a-codeai-public-reproduce-v1"
LICENSE_TEMPLATE = ROOT / "docs/final/artifacts/a_codeai_public_reproduce_apache2_LICENSE.txt"
PY = sys.executable

REPRODUCE_CI_YML = """name: reproduce-open-bench
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  reproduce:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install minimal deps
        run: pip install -q -r requirements-public-reproduce.txt
      - name: Onboard smoke (evidence + contributor validate)
        run: python3 scripts/run_compression_open_bench_onboard_smoke_v1.py
      - name: Verify reproduce pack
        run: test -f docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json
"""

REQUIREMENTS_TXT = """fastapi>=0.100
starlette>=0.27
pydantic>=2.0
httpx>=0.24
tiktoken>=0.5
jsonschema>=4.0
pytest>=7.0
"""

LEAK_SCAN_SUFFIXES = {".json", ".jsonl", ".md", ".env", ".yaml", ".yml", ".toml"}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if str(doc.get("schema")) != "a_codeai_public_reproduce_export_manifest_v1":
        raise SystemExit("export manifest schema mismatch")
    return doc


def _resolve_closure_paths(manifest: dict[str, Any]) -> list[str]:
    entries = manifest.get("entry_scripts") or []
    if not entries:
        return []
    cmd = [
        PY,
        "scripts/resolve_a_codeai_public_reproduce_export_closure_v1.py",
        "--out-json",
        "reports/tmp_export_closure_v1.json",
    ]
    for rel in entries:
        cmd.extend(["--entry", str(rel).replace("\\", "/")])
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    closure_path = ROOT / "reports/tmp_export_closure_v1.json"
    if not closure_path.is_file():
        return []
    doc = json.loads(closure_path.read_text(encoding="utf-8"))
    return list(doc.get("paths") or [])


def _collect_paths(manifest: dict[str, Any]) -> list[str]:
    rels: set[str] = set()
    for rel in manifest.get("paths") or []:
        rels.add(str(rel).replace("\\", "/"))
    for rel in _resolve_closure_paths(manifest):
        rels.add(rel.replace("\\", "/"))
    for prefix in manifest.get("path_prefixes") or []:
        pref = str(prefix).replace("\\", "/").rstrip("/")
        base = ROOT / pref
        if not base.is_dir():
            continue
        for fp in base.rglob("*"):
            if not fp.is_file():
                continue
            rel = fp.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or rel.endswith(".pyc") or rel.endswith(".bak"):
                continue
            rels.add(rel)
    return sorted(rels)


def _leak_check(rel: str, manifest: dict[str, Any]) -> str | None:
    low = rel.lower()
    for sub in manifest.get("deny_path_substrings") or []:
        if sub.lower() in low:
            return f"deny_path_substring:{sub}"
    name = Path(rel).name.lower()
    for pat in manifest.get("deny_filename_patterns") or []:
        if pat.lower() in name:
            return f"deny_filename_pattern:{pat}"
    return None


def _copy_file(src: Path, dest: Path, *, dry_run: bool) -> dict[str, Any]:
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return {
        "path": src.relative_to(ROOT).as_posix(),
        "sha256": _sha256(src),
        "bytes": src.stat().st_size,
    }


def materialize(
    *,
    out_dir: Path,
    manifest_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    all_paths = _collect_paths(manifest)
    copied: list[dict[str, Any]] = []
    missing: list[str] = []
    blocked: list[dict[str, str]] = []

    if out_dir.exists() and not dry_run:
        try:
            git_dir = out_dir / ".git"
            if git_dir.exists():
                for child in out_dir.iterdir():
                    if child.name == ".git":
                        continue
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
            else:
                shutil.rmtree(out_dir)
        except OSError:
            # Windows file-lock: fall back to in-place overwrite of tracked paths.
            pass
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    for rel_norm in all_paths:
        reason = _leak_check(rel_norm, manifest)
        if reason:
            blocked.append({"path": rel_norm, "reason": reason})
            continue
        src = ROOT / rel_norm
        if not src.is_file():
            missing.append(rel_norm)
            continue
        copied.append(_copy_file(src, out_dir / rel_norm, dry_run=dry_run))

    routed_note = ""
    dual_path = out_dir / "reports/compression_open_bench_dual_report_v1_latest.json"
    if dual_path.is_file():
        try:
            dual = json.loads(dual_path.read_text(encoding="utf-8"))
            for row in dual.get("corpora_and_skus") or []:
                if row.get("label") == "golden40_public_safe_routed" and row.get("non_zero_saving"):
                    raw = row.get("raw") or {}
                    routed_note = (
                        "\n## Measured open-bench headline (per-corpus · `[HYPO]` · SEND_GATE HOLD)\n\n"
                        f"- **golden40_public_safe_routed** · MKM-CHAT-D1 · N={row.get('case_count')}\n"
                        f"- raw token saving: **{raw.get('saving_pct_display')}%** · "
                        f"Jaccard **{raw.get('mean_jaccard_proxy')}**\n"
                        "- Not equivalent to frozen Track A 47.5% SLA.\n"
                        "- Stateless golden40 on same corpus may read 0% — cite routing SKU separately.\n\n"
                    )
                    break
        except (json.JSONDecodeError, OSError):
            routed_note = ""

    research_note = ""
    deck_path = out_dir / "docs/final/artifacts/compression_open_bench_persuasion_deck_v1_latest.json"
    if deck_path.is_file():
        try:
            deck = json.loads(deck_path.read_text(encoding="utf-8"))
            lit = deck.get("btrack_research_anchor_literal") or {}
            lit_raw = lit.get("raw") or {}
            if lit_raw.get("saving_pct_display"):
                research_note = (
                    "\n## B-track research (internal scenario only · not external headline)\n\n"
                    f"- CHAT-D1 **literal** on golden40: **{lit_raw.get('saving_pct_display')}%** · "
                    f"Jaccard **{lit_raw.get('mean_jaccard_proxy')}**\n"
                    "- See `reports/compression_open_bench_research_sweep_v1_latest.json`\n\n"
                )
        except (json.JSONDecodeError, OSError):
            research_note = ""

    customer_note = ""
    cust_poc_path = ROOT / "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json"
    if cust_poc_path.is_file():
        try:
            cust = json.loads(cust_poc_path.read_text(encoding="utf-8"))
            agg = cust.get("aggregate") or {}
            saving = float(agg.get("mean_token_saving_rate_proxy") or 0) * 100
            jacc = agg.get("mean_jaccard_proxy")
            passed = cust.get("cases_passed")
            total = cust.get("case_count")
            customer_note = (
                "\n## Customer-provided pilot (internal lane only · `customer_provided`)\n\n"
                f"- **wtt-premium-cs-customer-v1** · N={total} · pass {passed}/{total}\n"
                f"- raw token saving: **{saving:.2f}%** · Jaccard **{jacc}**\n"
                "- Separate from Track A active ~47.5% and contributor open-bench.\n"
                "- Rows 031-050 may be `[HYPO]` pilot derivations — not a new live customer upload.\n"
                "- Reproduce expand: `python3 scripts/expand_wtt_premium_cs_customer_live_n50_v1.py --write`\n"
                "- Artifact: `reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json`\n\n"
            )
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            customer_note = ""

    readme = (
        "# A-CODEAI public reproduce export (slim)\n\n"
        "SEND_GATE: HOLD — do not use as customer case study or merged marketing headline.\n"
        "`research_only` · B→A auto-merge prohibited.\n\n"
        f"{routed_note}{research_note}{customer_note}"
        "## One command (from repo root)\n\n"
        "```bash\n"
        "pip install -r requirements-public-reproduce.txt\n"
        "python3 scripts/run_compression_evidence_lv1_chain_v1.py --skip-handoff\n"
        "```\n\n"
        "Optional open-bench chain (includes golden40 routed PoC):\n\n"
        "```bash\n"
        "python3 scripts/run_compression_open_bench_chain_v1.py --skip-expand\n"
        "```\n\n"
        "## 10-minute onboard smoke (visitor + contributor validate)\n\n"
        "```bash\n"
        "pip install -r requirements-public-reproduce.txt\n"
        "python3 scripts/run_compression_open_bench_onboard_smoke_v1.py\n"
        "```\n\n"
        "Windows: `powershell -File scripts/Invoke-CompressionOpenBenchOnboardSmoke_v1.ps1`\n\n"
        "Does not run commander mirror push or default customer n50 path. "
        "Contribute via PR — see `CONTRIBUTING_OPEN_BENCH.md`.\n\n"
        "FAIL-COMP-004: per-SKU metrics only; never merge Track A / handoff / prospect %.\n\n"
        "## Enterprise pre-audit intake (web form · separate funnel)\n\n"
        "- Tier-0 **free pre-audit** queue (masked JSONL sample review): "
        "[app.jema-ai.com/enterprise/apply](https://app.jema-ai.com/enterprise/apply)\n"
        "- Not auto-approval, not SLA or Track A headline guarantee; "
        "open-bench metrics above are not a submission outcome.\n\n"
        "## Community contributions (contributor_provided · SEND_GATE HOLD)\n\n"
        "See `CONTRIBUTING_OPEN_BENCH.md` — masked JSONL under `data/*/contributions/`; "
        "`contributor_provided=true`, `customer_provided=false`; no Track A / 47.5% headline.\n\n"
        "## License\n\n"
        "Apache License 2.0 — see [LICENSE](LICENSE). "
        "Open-bench reproduce only; SEND_GATE HOLD unchanged.\n"
    )

    ci_path = ".github/workflows/reproduce_ci.yml"
    if not dry_run:
        (out_dir / ci_path).parent.mkdir(parents=True, exist_ok=True)
        (out_dir / ci_path).write_text(REPRODUCE_CI_YML, encoding="utf-8")
        (out_dir / "README.md").write_text(readme, encoding="utf-8")
        if LICENSE_TEMPLATE.is_file():
            shutil.copy2(LICENSE_TEMPLATE, out_dir / "LICENSE")
        (out_dir / "requirements-public-reproduce.txt").write_text(REQUIREMENTS_TXT, encoding="utf-8")
        (out_dir / ".gitignore").write_text("__pycache__/\n*.pyc\n.pytest_cache/\n", encoding="utf-8")
        (out_dir / "reports").mkdir(parents=True, exist_ok=True)
        (out_dir / "docs/final/artifacts").mkdir(parents=True, exist_ok=True)

    leak_scan_hits: list[str] = []
    secret_re = re.compile(
        r"(AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{20,}|-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----)",
        re.I,
    )
    if not dry_run:
        for fp in out_dir.rglob("*"):
            if not fp.is_file():
                continue
            if fp.suffix.lower() not in LEAK_SCAN_SUFFIXES:
                continue
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if secret_re.search(text):
                leak_scan_hits.append(str(fp.relative_to(out_dir)).replace("\\", "/"))

    deny_blocked = [b for b in blocked if str(b.get("reason", "")).startswith("deny_")]
    unexpected_blocked = [b for b in blocked if b not in deny_blocked]
    ok = len(missing) == 0 and len(unexpected_blocked) == 0 and len(leak_scan_hits) == 0
    return {
        "schema": "a_codeai_public_reproduce_materialize_report_v1",
        "generated_at_utc": _utc(),
        "out_dir": str(out_dir),
        "dry_run": dry_run,
        "materialize_ok": ok,
        "path_candidates": len(all_paths),
        "copied_count": len(copied),
        "copied": copied,
        "missing": missing,
        "blocked": blocked,
        "leak_scan_hits": leak_scan_hits,
        "ci_workflow": ci_path,
        "boundary_ack": "FAIL-COMP-004 — public mirror is technical reproduce only; SEND_GATE HOLD.",
    }


def verify_chain(out_dir: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [PY, "scripts/run_compression_evidence_lv1_chain_v1.py", "--skip-handoff"],
        cwd=str(out_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    chain_path = out_dir / "reports/compression_evidence_lv1_chain_v1_latest.json"
    chain_ok = False
    if chain_path.is_file():
        try:
            chain_ok = bool(json.loads(chain_path.read_text(encoding="utf-8")).get("chain_ok"))
        except (json.JSONDecodeError, OSError):
            chain_ok = False
    return {
        "exit_code": proc.returncode,
        "chain_ok": chain_ok and proc.returncode == 0,
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-1500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR_DEFAULT)
    ap.add_argument("--manifest-json", type=Path, default=MANIFEST_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify-chain", action="store_true", help="Run evidence chain inside export dir after copy")
    ap.add_argument(
        "--report-json",
        type=Path,
        default=ROOT / "reports/a_codeai_public_reproduce_materialize_v1_latest.json",
    )
    args = ap.parse_args()

    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    manifest_path = args.manifest_json if args.manifest_json.is_absolute() else ROOT / args.manifest_json
    report_path = args.report_json if args.report_json.is_absolute() else ROOT / args.report_json

    doc = materialize(out_dir=out_dir, manifest_path=manifest_path, dry_run=args.dry_run)
    if args.verify_chain and not args.dry_run and doc["materialize_ok"]:
        doc["verify_chain"] = verify_chain(out_dir)
        doc["materialize_ok"] = bool(doc["materialize_ok"] and doc["verify_chain"].get("chain_ok"))

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["materialize_ok"],
                "out_dir": str(out_dir),
                "copied_count": doc["copied_count"],
                "missing_count": len(doc["missing"]),
                "verify_chain_ok": (doc.get("verify_chain") or {}).get("chain_ok"),
                "report": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["materialize_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
