#!/usr/bin/env python3
"""Build MKM formula SSOT bundle: manifest master table, core20 lines, 75-formula list."""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAULT_INGEST = Path(r"G:/공유 드라이브/MKM_DATA_VAULT/vault/h_drive_knowledge_ingest/2026-04-09")
MANIFEST = VAULT_INGEST / "manifest_math_constitution_theory_focus_2026-04-09.csv"
CORE20 = VAULT_INGEST / "formula_precision_core20"
OUT_DIR = ROOT / "docs/final/artifacts"
SUMMARY_PATH = ROOT / "docs/verified_knowledge_base/mkm12_mathematics/core_formulas_summary.json"
OUT_75_MD = ROOT / "docs/final/MKM12_75개_수학공식_전체목록_2026-01-31.md"
VAULT_75_CATALOG = (
    ROOT / "docs/final/vault_mirror/mkm12_mathematics/MKM12_75개_수학공식_전체목록_2026-01-31.md"
)
VAULT_FORMULA_INDEX = (
    ROOT / "docs/final/vault_mirror/mkm12_mathematics/MKM12_수학공식_인덱스_2026-01-31.md"
)
CONSTITUTION_FULL = ROOT / "docs/final/MKM12_수학_헌법_2026-01-31.md"

CHAPTER_HDR_RE = re.compile(r"^### 제(\d+)장:\s*([^-]+)\s*-\s*(\d+)개")
CATALOG_LINE_RE = re.compile(r"^(\d+)\.\s+(.+)$")
INDEX_HDR_RE = re.compile(r"^#### 공식 (\d+-\d+):\s*(.+)$")
CONSTITUTION_HDR_RE = re.compile(r"^### 공식 (\d+-\d+):\s*(.+)$")
SUB_LABEL_RE = re.compile(r"^\*\*(.+?)\*\*:?\s*$")

LATEX_RE = re.compile(r"\$[^$]+\$|\\\[[\s\S]*?\\\]|\\\([^)]+\\\)")
CODE_ASSIGN = re.compile(r"^\s*(?:[a-zA-Z_][\w.]*\s*=\s*.+|return\s+.+)")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def grade_formula(tags: str, path_str: str) -> str:
    p = path_str.lower()
    if any(x in p for x in ("test_", "node_modules", "mpmath", "sympy", "__pycache__")):
        return "EXCLUDE"
    repo_impl = (
        "mkm_myeongni_math.py",
        "gematria_myeongri_math",
        "gematria_to_4d_bridge",
        "unified_field_theory_engine",
        "domainlambdacalculator",
        "bigquery_4d_dynamics",
    )
    if any(r in p for r in repo_impl):
        return "FACT"
    if "4d_dynamics" in tags and p.endswith(".py"):
        return "HYPO"
    if "formula" in tags:
        return "HYPO"
    return "HYPO"


def extract_lines(text: str, ext: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for m in LATEX_RE.finditer(text):
        hits.append(("latex", m.group(0).strip()))
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or len(s) < 8:
            continue
        if ext == ".py":
            if CODE_ASSIGN.match(line) and any(c in s for c in "=+-*/"):
                if s.startswith(("import ", "from ", "def ", "class ", "#")):
                    continue
                hits.append(("code", f"L{i}:{s[:220]}"))
        else:
            if "$" in s or re.search(r"[a-zA-Z_]\w*\s*=\s*[^=]", s):
                if re.search(
                    r"[+\-*/^]|dx/dt|geumhwa|renorm|clamp|lambda|λ|cosine|l2",
                    s,
                    re.I,
                ):
                    hits.append(("eq", f"L{i}:{s[:220]}"))
    return hits[:25]


def task1_manifest_master(ts: str) -> tuple[int, Path, Path]:
    rows: list[dict[str, str]] = []
    tag_filter = {"formula", "4d_dynamics"}
    with MANIFEST.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            tags_set = set((row.get("tags") or "").split(";"))
            if not (tags_set & tag_filter):
                continue
            cp = Path(row["copied_path"])
            if not cp.is_file():
                cp = Path(row.get("source_path", ""))
            grade = "MISSING"
            expr = ""
            extract_count = 0
            if cp.is_file():
                text = cp.read_text(encoding="utf-8", errors="replace")
                hits = extract_lines(text, cp.suffix.lower())
                expr = " | ".join(h[1] for h in hits[:5])
                extract_count = len(hits)
                grade = grade_formula(row.get("tags", ""), str(cp))
            if grade == "EXCLUDE":
                continue
            rows.append(
                {
                    "formula_id": f"M-{len(rows) + 1:04d}",
                    "name": cp.name if str(cp) else row.get("copied_path", "")[-40:],
                    "latex_or_expr": expr[:500],
                    "vault_copied_path": row["copied_path"],
                    "source_path": row.get("source_path", ""),
                    "tags": row.get("tags", ""),
                    "grade": grade,
                    "extract_count": str(extract_count),
                }
            )

    csv_path = OUT_DIR / "mkm_formula_master_table_v1_latest.csv"
    md_path = OUT_DIR / "mkm_formula_master_table_v1_latest.md"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if rows:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    md_lines = [
        "# MKM Formula Master Table v1",
        f"generated_at_utc: {ts}",
        f"manifest: `{MANIFEST}`",
        "filter_tags: formula, 4d_dynamics",
        f"row_count: {len(rows)}",
        "",
        "| formula_id | name | grade | tags | extract_count | vault_copied_path |",
        "|---|---|---|---|---:|---|",
    ]
    for r in rows:
        p = r["vault_copied_path"].replace("|", "/")
        if len(p) > 90:
            p = "..." + p[-87:]
        md_lines.append(
            f"| {r['formula_id']} | {r['name'][:36]} | {r['grade']} | {r['tags']} | {r['extract_count']} | `{p}` |"
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return len(rows), csv_path, md_path


def task2_core20_lines(ts: str) -> tuple[int, Path, Path]:
    core_rows: list[dict[str, str]] = []
    if CORE20.is_dir():
        for fp in sorted(CORE20.iterdir()):
            if not fp.is_file():
                continue
            text = fp.read_text(encoding="utf-8", errors="replace")
            for kind, expr in extract_lines(text, fp.suffix.lower()):
                core_rows.append(
                    {"core20_file": fp.name, "kind": kind, "expr": expr}
                )

    csv_path = OUT_DIR / "mkm_formula_precision_core20_lines_v1_latest.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["core20_file", "kind", "expr"])
        w.writeheader()
        w.writerows(core_rows)

    md_path = OUT_DIR / "mkm_formula_precision_core20_lines_v1_latest.md"
    md_lines = [
        "# Formula Precision Core20 Lines v1",
        f"generated_at_utc: {ts}",
        f"source_dir: `{CORE20}`",
        f"line_count: {len(core_rows)}",
        "",
    ]
    for r in core_rows[:100]:
        md_lines.append(f"- **{r['core20_file']}** ({r['kind']}): `{r['expr'][:140]}`")
    if len(core_rows) > 100:
        md_lines.append(f"\n... and {len(core_rows) - 100} more (see CSV)")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return len(core_rows), csv_path, md_path


def _normalize_name(s: str) -> str:
    return re.sub(r"\s+", "", s.lower().replace("→", "").replace("(", "").replace(")", ""))


def _parse_vault_75_catalog(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    current_chapter = "vault_pending"
    current_chapter_name = ""
    by_slot: dict[int, dict[str, object]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        ch = CHAPTER_HDR_RE.match(line.strip())
        if ch:
            current_chapter = f"chapter_{ch.group(1)}"
            current_chapter_name = ch.group(2).strip()
            continue
        row = CATALOG_LINE_RE.match(line.strip())
        if not row:
            continue
        slot = int(row.group(1))
        if slot < 1 or slot > 75:
            continue
        by_slot[slot] = {
            "slot": slot,
            "id": f"F-{slot:03d}",
            "category": current_chapter,
            "chapter_name": current_chapter_name,
            "name": row.group(2).strip(),
            "formula": "",
            "purpose": current_chapter_name,
            "grade": "HYPO",
            "source": str(path.relative_to(ROOT)).replace("\\", "/"),
        }
    return [by_slot[i] for i in sorted(by_slot)]


def _parse_formula_index_exprs(path: Path) -> dict[str, dict[str, str]]:
    """Parse core-24 index: id -> {name, formula}."""
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, dict[str, str]] = {}
    current_id = ""
    current_name = ""
    buf: list[str] = []
    in_block = False

    def flush() -> None:
        nonlocal current_id, current_name, buf, in_block
        if not current_id:
            return
        expr = " ".join(buf).strip()
        expr = re.sub(r"\s+", " ", expr)[:500]
        out[current_id] = {"name": current_name, "formula": expr}
        current_id = ""
        current_name = ""
        buf = []
        in_block = False

    for line in text.splitlines():
        hdr = INDEX_HDR_RE.match(line.strip())
        if hdr:
            flush()
            current_id = hdr.group(1)
            current_name = hdr.group(2).strip()
            continue
        if line.strip() == "$$":
            if in_block:
                flush()
            else:
                in_block = True
            continue
        if in_block and line.strip():
            buf.append(line.strip())
    flush()
    return out


def _store_constitution_expr(
    out: dict[str, dict[str, str]],
    key: str,
    current_id: str,
    current_name: str,
    expr: str,
) -> None:
    if not key or not expr:
        return
    norm = _normalize_name(key)
    if norm in out:
        return
    out[norm] = {
        "id": current_id,
        "name": current_name if key == current_name else key,
        "formula": expr[:500],
    }


def _parse_constitution_exprs(path: Path) -> dict[str, dict[str, str]]:
    """Parse full constitution: normalized name/label -> {id, formula}."""
    if not path.is_file():
        return {}
    out: dict[str, dict[str, str]] = {}
    current_id = ""
    current_name = ""
    current_sublabel = ""
    buf: list[str] = []
    in_block = False
    section_has_primary = False

    def flush_block() -> None:
        nonlocal buf, in_block, section_has_primary, current_sublabel
        if not current_id:
            buf = []
            in_block = False
            return
        expr = re.sub(r"\s+", " ", " ".join(buf).strip())[:500]
        if expr:
            if not section_has_primary:
                _store_constitution_expr(out, current_name, current_id, current_name, expr)
                section_has_primary = True
            if current_sublabel:
                _store_constitution_expr(
                    out, current_sublabel, current_id, current_name, expr
                )
        buf = []
        in_block = False

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        hdr = CONSTITUTION_HDR_RE.match(line.strip())
        if hdr:
            flush_block()
            current_id = hdr.group(1)
            current_name = hdr.group(2).strip()
            current_sublabel = ""
            section_has_primary = False
            continue
        if not current_id:
            continue
        sub = SUB_LABEL_RE.match(line.strip())
        if sub:
            flush_block()
            current_sublabel = sub.group(1).strip()
            continue
        if line.strip() == "$$":
            if in_block:
                flush_block()
            else:
                in_block = True
            continue
        if in_block and line.strip():
            buf.append(line.strip())
    flush_block()
    return out


def _enrich_from_constitution(
    expanded: list[dict[str, object]],
    constitution_exprs: dict[str, dict[str, str]],
) -> None:
    alias_keys: dict[str, list[str]] = {
        "사전확률계산": ["사전확률강도적용", "prior", "사전확률"],
        "사후확률계산": ["사후확률계산", "posterior", "사후확률"],
        "lambda기반예측": ["명리λ예측", "예측보정", "lambda기반예측"],
    }

    def _pick_meta(norm: str) -> dict[str, str] | None:
        for key, meta in constitution_exprs.items():
            if key in norm or norm in key:
                return meta
        for aliases in alias_keys.values():
            if norm in aliases or any(a in norm for a in aliases):
                for alias in aliases:
                    if alias in constitution_exprs:
                        return constitution_exprs[alias]
        for alias_list in alias_keys.values():
            if norm in alias_list:
                for alias in alias_list:
                    for key, meta in constitution_exprs.items():
                        if alias in key or key in alias:
                            return meta
        if norm in alias_keys:
            for alias in alias_keys[norm]:
                for key, meta in constitution_exprs.items():
                    if alias in key or key in alias:
                        return meta
        return None

    for entry in expanded:
        if entry.get("formula"):
            continue
        name = str(entry.get("name", ""))
        norm = _normalize_name(name)
        best = _pick_meta(norm)
        if not best:
            continue
        entry["formula"] = best.get("formula", "")
        entry["constitution_id"] = best.get("id", "")
        entry["source"] = (
            str(CONSTITUTION_FULL.relative_to(ROOT)).replace("\\", "/")
            + f"#{best.get('id', '')}"
        )


def _enrich_from_index_and_summary(
    expanded: list[dict[str, object]],
    index_exprs: dict[str, dict[str, str]],
    summary_by_name: dict[str, dict[str, str]],
) -> None:
    for entry in expanded:
        name = str(entry.get("name", ""))
        norm = _normalize_name(name)
        for fid, meta in index_exprs.items():
            if _normalize_name(meta["name"]) in norm or norm in _normalize_name(meta["name"]):
                entry["id"] = fid
                if meta.get("formula"):
                    entry["formula"] = meta["formula"]
                entry["source"] = (
                    str(VAULT_FORMULA_INDEX.relative_to(ROOT)).replace("\\", "/")
                    + f"#{fid}"
                )
                break
        sm = summary_by_name.get(norm)
        if sm and not entry.get("formula"):
            entry["formula"] = sm.get("formula", "")
            if sm.get("id"):
                entry["id"] = sm["id"]


def _vault_source_candidates() -> list[str]:
    hits: list[str] = []
    mc = VAULT_INGEST / "math_constitution_theory_focus"
    if mc.is_dir():
        for p in mc.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in {".md", ".json"}:
                continue
            name = p.name
            if any(k in name for k in ("75", "수학공식", "수학헌법", "MKM12_수학", "인덱스")):
                hits.append(str(p))
            if len(hits) >= 25:
                break
    return hits


def task3_75_formulas(ts: str) -> tuple[int, Path, Path, Path]:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    total_target = int(summary.get("verification_status", {}).get("total_formulas", 75))
    refs = summary.get("references", {})

    summary_by_name: dict[str, dict[str, str]] = {}
    for cat in (summary.get("formula_categories") or {}).values():
        for e in cat.get("formulas", []):
            name = str(e.get("name", ""))
            summary_by_name[_normalize_name(name)] = {
                "id": str(e.get("id", "")),
                "formula": str(e.get("formula", e.get("value", ""))),
            }

    vault_catalog = _parse_vault_75_catalog(VAULT_75_CATALOG)
    index_exprs = _parse_formula_index_exprs(VAULT_FORMULA_INDEX)
    constitution_exprs = _parse_constitution_exprs(CONSTITUTION_FULL)
    expanded: list[dict[str, object]] = []

    if len(vault_catalog) == total_target:
        expanded = vault_catalog
        _enrich_from_index_and_summary(expanded, index_exprs, summary_by_name)
        _enrich_from_constitution(expanded, constitution_exprs)
        documented = len(expanded)
        unrecovered = 0
    else:
        idx = 0
        for cat_key, cat in (summary.get("formula_categories") or {}).items():
            count = int(cat.get("count", 0))
            existing = cat.get("formulas", [])
            for i in range(count):
                idx += 1
                if i < len(existing):
                    e = existing[i]
                    expanded.append(
                        {
                            "slot": idx,
                            "id": e.get("id", f"{cat_key}-{i + 1}"),
                            "category": cat_key,
                            "name": e.get("name", ""),
                            "formula": e.get("formula", e.get("value", "")),
                            "purpose": e.get("purpose", ""),
                            "grade": "HYPO",
                            "source": "core_formulas_summary.json",
                        }
                    )
                else:
                    expanded.append(
                        {
                            "slot": idx,
                            "id": f"{cat_key}-{i + 1}",
                            "category": cat_key,
                            "name": f"(slot) {cat.get('description', cat_key)} #{i + 1}",
                            "formula": "",
                            "purpose": cat.get("description", ""),
                            "grade": "HYPO",
                            "source": "core_formulas_summary.json (count-only)",
                        }
                    )
        documented = len(expanded)
        for slot in range(documented + 1, total_target + 1):
            expanded.append(
                {
                    "slot": slot,
                    "id": f"UNRECOVERED-{slot:03d}",
                    "category": "vault_pending",
                    "name": "(원천 미동기화)",
                    "formula": "",
                    "purpose": "See references.all_75_formulas / vault seal doc",
                    "grade": "HYPO",
                    "source": str(
                        refs.get("all_75_formulas", "mkm_vertex_ai_upload (not in workspace)")
                    ),
                }
            )
        unrecovered = max(0, total_target - documented)

    vault_hits = _vault_source_candidates()
    documented_with_expr = sum(1 for x in expanded if x.get("formula"))
    json_path = OUT_DIR / "mkm12_75_formulas_ssot_v1_latest.json"
    refs = dict(summary.get("references", {}))
    refs.update(
        {
            "worldview_constitution": "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
            "worldview_section": "5",
            "ascii_ssot_pointer": "docs/final/MKM12_75_FORMULAS_SSOT_V1.md",
            "theory_mathematization_canon": (
                "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md"
            ),
            "promotion_registry": (
                "docs/final/artifacts/mkm_theory_formula_promotion_registry_v1_latest.json"
            ),
            "crosslink_bridge": (
                "docs/final/artifacts/worldview_formula_crosslink_bridge_v1_latest.json"
            ),
        }
    )
    payload = {
        "schema": "mkm12_75_formulas_ssot_v1",
        "generated_at_utc": ts,
        "constitution_version": summary["mkm12_mathematics"]["version"],
        "total_slots": total_target,
        "documented_from_summary": documented,
        "unrecovered_slots": unrecovered,
        "vault_catalog_slots": len(vault_catalog),
        "documented_with_expr": documented_with_expr,
        "axis_note": (
            "Planning C(소음) vs runtime M(Material): production wiring uses S-L-K-M only."
        ),
        "references": refs,
        "vault_source_candidates": vault_hits,
        "formulas": expanded,
        "repo_implemented_facts": [
            {
                "id": "gematria_blend",
                "path": "tools/myeongni/gematria_myeongri_math_v1.py",
                "expr": "hybrid = renorm((1-w)*vanilla + w*myeongri)",
                "grade": "FACT",
            },
            {
                "id": "gematria_4d_bridge",
                "path": "scripts/core/gematria_to_4d_bridge.py",
                "expr": "S,L,K from gematria sums mod 101; M=1-(S+L+K)",
                "grade": "FACT",
            },
            {
                "id": "myeongni_d_out",
                "path": "scripts/myeongni_lens_v1/mkm_myeongni_math.py",
                "expr": "d_out=clamp(d_school+0.22*ten_god_balance-0.18*jijangan_pressure)",
                "grade": "FACT",
            },
            {
                "id": "geumhwa",
                "path": "docs/verified_knowledge_base/unified_field_theory/geumhwa_exchange.json",
                "expr": "geumhwa_index=K*(1-M)*earth_mediation_factor",
                "grade": "FACT",
            },
        ],
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    mk = summary["mkm12_mathematics"]
    if unrecovered:
        recovery_note = (
            f"> **복구 상태:** 카테고리 JSON에서 **{documented}**식 명시 + "
            f"**{unrecovered}**식은 원천(`{refs.get('final_sealed_version', 'Vault')}`) 미러 대기."
        )
    else:
        recovery_note = (
            f"> **복구 상태:** Vault 75식 카탈로그 **{len(vault_catalog)}**슬롯 입고 · "
            f"수식 문자열 **{documented_with_expr}**식 · UNRECOVERED **0**."
        )
    md_lines = [
        "# MKM12 75개 수학공식 전체목록 (SSOT 복구 v1)",
        "",
        f"**generated_at_utc:** {ts}",
        f"**헌법 버전:** {mk['version']} (봉인 {mk['seal_date']})",
        "",
        "> **Fact-Lock:** 연구·Moat 인덱스. Track A 불변식은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` + 호출 가능 `.py`만.",
        "",
        "> **축 경고:** 기획 **C(소음)** ≠ 운영 **M(Material)**. MS-PASTE·배선은 **S-L-K-M**.",
        "",
        "## 등급",
        "- **FACT**: 레포 스크립트·검증 JSON 고정식",
        "- **HYPO**: 헌법·연구; 프로덕션 자동 결선 금지",
        "",
        "## 75 슬롯",
        "",
        recovery_note,
        "",
        "| slot | id | category | name | formula/value | grade |",
        "|---:|---|---|---|---|---|",
    ]
    for x in expanded:
        f = str(x.get("formula") or "")[:55].replace("|", "/")
        md_lines.append(
            f"| {x['slot']} | {x['id']} | {x['category']} | {str(x['name'])[:32]} | {f} | {x['grade']} |"
        )
    md_lines.extend(["", "## 레포 FACT 구현", ""])
    for r in payload["repo_implemented_facts"]:
        md_lines.append(f"- **{r['id']}** (`{r['grade']}`): `{r['path']}` — `{r['expr']}`")
    md_lines.extend(
        [
            "",
            "## 머신 SSOT",
            f"- `docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json`",
            f"- `docs/verified_knowledge_base/mkm12_mathematics/core_formulas_summary.json`",
            "",
            "## Vault 원천 후보",
        ]
    )
    for v in vault_hits[:12]:
        md_lines.append(f"- `{v}`")
    OUT_75_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_75_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return len(expanded), OUT_75_MD, json_path, json_path


def main() -> int:
    ts = utc_now()
    n1, p1c, p1m = task1_manifest_master(ts)
    n2, p2c, p2m = task2_core20_lines(ts)
    n3, p3m, p3j, _ = task3_75_formulas(ts)
    report = {
        "schema": "mkm_formula_ssot_bundle_report_v1",
        "generated_at_utc": ts,
        "task1_manifest_rows": n1,
        "task1_csv": str(p1c),
        "task1_md": str(p1m),
        "task2_core20_lines": n2,
        "task2_csv": str(p2c),
        "task2_md": str(p2m),
        "task3_75_slots": n3,
        "task3_md": str(p3m),
        "task3_json": str(p3j),
    }
    out = OUT_DIR / "mkm_formula_ssot_bundle_report_v1_latest.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
