#!/usr/bin/env python3
"""
Premium B-track multi-lens report packager (v0 / v0.5).

Sync-only: stub lens workers from schema example; optional `--mode best-effort`
ingests independent-lens JSON from disk; optional tracked **offline RAG bundle**
(keyword hits over bundle + optional `--rag-corpus-scan-dir`; no API). Optional `--async-simulate`
fills `async_job` for queue-shaped handoff (sync single-shot, no Redis). Optional `--async-queue-enqueue`
appends one line to `premium_multilens_job_queue_stub_v1.py` JSONL (v0 file queue, no worker).

Structural coordinator join, disk MD + JSON matching premium_btrack_multilens_report_v1 schema.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

Mode = Literal["stub", "best-effort"]


def _repo_root() -> Path:
    env = (Path(__file__).resolve().parent.parent).resolve()
    raw = os.environ.get("MKM_WORKSPACE_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    return env


def _load_premium_multilens_queue_stub_v1() -> Any:
    stub_path = Path(__file__).resolve().parent / "premium_multilens_job_queue_stub_v1.py"
    name = "_premium_multilens_queue_stub_v1"
    spec = importlib.util.spec_from_file_location(name, stub_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load queue stub module: {stub_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _utc_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _posix_under_root(path: Path, root: Path) -> str:
    rp = path.resolve()
    rr = root.resolve()
    try:
        return rp.relative_to(rr).as_posix()
    except ValueError:
        return rp.as_posix()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_example(example_path: Path) -> dict[str, Any]:
    return json.loads(example_path.read_text(encoding="utf-8"))


def _load_rag_bundle(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _rag_query_chunks_from_blob(lens_id: str, blob: dict[str, Any]) -> str:
    chunks: list[str] = []
    note = blob.get("note")
    if note:
        chunks.append(str(note))
    sc = blob.get("scores")
    if isinstance(sc, dict):
        chunks.append(json.dumps(sc, ensure_ascii=False))
    mso = blob.get("myeongri_stream_outputs")
    if isinstance(mso, dict):
        chunks.append(str(mso.get("rationale", "")))
    sso = blob.get("sasang_stream_outputs")
    if isinstance(sso, dict):
        chunks.append(str(sso.get("rationale", "")))
    lso = blob.get("logos_stream_outputs")
    if isinstance(lso, dict):
        chunks.append(str(lso.get("rationale", "")))
    nsg = blob.get("narrative_snippet_guarded")
    if nsg:
        chunks.append(str(nsg))
    q = " ".join(chunks).strip()
    return q if q else f"{lens_id} B-track offline RAG query"


def _rag_query_tokens(q: str) -> list[str]:
    tokens = re.findall(r"[\w가-힣]{3,}", q.lower())
    seen: set[str] = set()
    uniq: list[str] = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        uniq.append(t)
        if len(uniq) >= 24:
            break
    return uniq


def _score_doc(tokens: list[str], text: str) -> int:
    tl = text.lower()
    return sum(1 for t in tokens if t in tl)


def scan_rag_corpus_documents(scan_dir: Path, root: Path, *, max_files: int = 48, max_total_bytes: int = 200_000) -> list[dict[str, Any]]:
    """Shallow scan of *.txt / *.md / *.json in a directory into excerpt docs (B-track, local only)."""
    if not scan_dir.is_dir():
        return []
    per_cap = max(4096, max_total_bytes // max(1, max_files))
    docs: list[dict[str, Any]] = []
    total = 0
    try:
        candidates = sorted(
            p for p in scan_dir.iterdir() if p.is_file() and p.suffix.lower() in (".txt", ".md", ".json")
        )
    except OSError:
        return []
    for p in candidates[:max_files]:
        try:
            raw = p.read_bytes()
        except OSError:
            continue
        chunk = raw[:per_cap]
        try:
            text = chunk.decode("utf-8", errors="replace")
        except Exception:
            continue
        try:
            rel = _posix_under_root(p, root)
        except Exception:
            rel = p.as_posix()
        docs.append(
            {
                "source_id": f"scan:{rel}"[:512],
                "uri": p.resolve().as_posix()[:2048],
                "license_note": "Scanned from --rag-corpus-scan-dir (local excerpt; B-track).",
                "text": text,
            }
        )
        total += len(chunk)
        if total >= max_total_bytes:
            break
    return docs


def _build_rag_from_entries(
    *,
    lens_id: str,
    disk_blob: dict[str, Any],
    entries: list[dict[str, Any]],
    max_hits: int = 5,
    corpus_id: str = "premium_multilens_rag_offline_v1",
) -> dict[str, Any] | None:
    q_line = _rag_query_chunks_from_blob(lens_id, disk_blob)[:4000]
    tokens = _rag_query_tokens(q_line)
    if not entries:
        return None
    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in entries:
        if not isinstance(doc, dict):
            continue
        text = str(doc.get("text", ""))
        sc = _score_doc(tokens, text)
        if sc > 0:
            scored.append((sc, doc))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("source_id", ""))))
    if not scored:
        scored = [(0, e) for e in entries if isinstance(e, dict)][:max_hits]
    if not scored:
        return None
    hits: list[dict[str, Any]] = []
    for i, (_sc, doc) in enumerate(scored[:max_hits]):
        band = "A" if i == 0 else ("B" if i < 3 else "C")
        text = str(doc.get("text", ""))
        hit: dict[str, Any] = {
            "source_id": str(doc.get("source_id", "unknown"))[:512],
            "snippet": (text[:7800] if text else "(empty)")[:8000],
            "confidence_band": band,
        }
        uri = doc.get("uri")
        if isinstance(uri, str) and uri.strip():
            hit["uri"] = uri[:2048]
        lic = doc.get("license_note")
        if isinstance(lic, str) and lic.strip():
            hit["license_note"] = lic[:2000]
        hits.append(hit)
    return {
        "corpus_id": corpus_id[:256],
        "retrieval_runs": [
            {
                "run_id": f"disk_kw_{lens_id}_v1",
                "query": q_line,
                "hits": hits,
            }
        ],
    }


def enrich_lenses_rag_offline(
    *,
    mode: Mode,
    root: Path,
    lenses: list[dict[str, Any]],
    disk_blobs: dict[str, dict[str, Any] | None],
    bundle_path: Path | None,
    scan_dir: Path | None,
) -> str | None:
    """Merge bundle + optional scan-dir excerpts into lens rag. Returns caveat note or None."""
    if mode != "best-effort":
        return None
    scan_docs = scan_rag_corpus_documents(scan_dir, root) if scan_dir else []
    bundle: dict[str, Any] | None = None
    ent_root: dict[str, Any] | None = None
    if bundle_path is not None and bundle_path.is_file():
        bundle = _load_rag_bundle(bundle_path)
        er = bundle.get("entries") if isinstance(bundle, dict) else None
        ent_root = er if isinstance(er, dict) else None

    if not scan_docs and not ent_root:
        return None

    used = False
    parts: list[str] = []
    if bundle_path is not None and bundle_path.is_file() and ent_root:
        parts.append(f"bundle=`{_posix_under_root(bundle_path, root)}`")
    if scan_dir is not None:
        try:
            srel = _posix_under_root(scan_dir, root)
        except Exception:
            srel = scan_dir.resolve().as_posix()
        parts.append(f"scan_dir=`{srel}`")

    for lens in lenses:
        if not isinstance(lens, dict):
            continue
        lid = str(lens.get("lens_id", ""))
        blob = (disk_blobs or {}).get(lid)
        if not isinstance(blob, dict):
            continue
        raw: list[dict[str, Any]] = []
        if ent_root:
            br = ent_root.get(lid)
            if isinstance(br, list):
                raw.extend([x for x in br if isinstance(x, dict)])
        raw.extend(scan_docs)
        if not raw:
            continue
        rag = _build_rag_from_entries(lens_id=lid, disk_blob=blob, entries=raw, max_hits=5)
        if rag and isinstance(rag.get("retrieval_runs"), list) and rag["retrieval_runs"]:
            lens["rag"] = rag
            used = True
    if not used:
        return None
    return "offline RAG: " + "; ".join(parts) if parts else "offline RAG: scan/bundle"


def enrich_lenses_rag_from_disk_bundle(
    *,
    mode: Mode,
    root: Path,
    lenses: list[dict[str, Any]],
    disk_blobs: dict[str, dict[str, Any] | None],
    bundle_path: Path | None,
) -> str | None:
    """Backward-compatible wrapper: bundle only, no scan dir."""
    return enrich_lenses_rag_offline(
        mode=mode,
        root=root,
        lenses=lenses,
        disk_blobs=disk_blobs,
        bundle_path=bundle_path,
        scan_dir=None,
    )


def default_independent_lens_paths(root: Path) -> dict[str, Path]:
    art = root / "docs" / "final" / "artifacts"
    return {
        "myeongni": art / "myeongni_independent_lens_latest.json",
        "sasang": art / "sasang_independent_lens_latest.json",
        "logos": art / "logos_independent_lens_latest.json",
    }


def attach_disk_engine_paths(
    *,
    root: Path,
    lenses: list[dict[str, Any]],
    mode: Mode,
    overrides: dict[str, Path],
) -> dict[str, dict[str, Any] | None]:
    """When mode=best-effort, set engine_artifact_paths from disk and return blobs per lens_id."""
    blobs: dict[str, dict[str, Any] | None] = {}
    if mode != "best-effort":
        for lens in lenses:
            if isinstance(lens, dict) and lens.get("lens_id"):
                blobs[str(lens["lens_id"])] = None
        return blobs

    defaults = default_independent_lens_paths(root)
    for lens in lenses:
        if not isinstance(lens, dict):
            continue
        lid = str(lens.get("lens_id", ""))
        if lid not in defaults:
            blobs[lid] = None
            continue
        path = overrides.get(lid) or defaults[lid]
        path = path.resolve()
        if not path.is_file():
            print(f"WARN: best-effort missing artifact for lens={lid}: {path}", file=sys.stderr)
            blobs[lid] = None
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"WARN: best-effort failed to read JSON lens={lid}: {e}", file=sys.stderr)
            blobs[lid] = None
            continue
        lens["engine_artifact_paths"] = [_posix_under_root(path, root)]
        blobs[lid] = data
    return blobs


def _disk_snapshot_lines_myeongni(blob: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        f"- artifact.schema: `{blob.get('schema')}` version=`{blob.get('version')}` ts=`{blob.get('ts_utc')}`",
    ]
    sc = blob.get("scores")
    if isinstance(sc, dict):
        lines.append(f"- scores.direction_score: {sc.get('direction_score')}")
        lines.append(f"- scores.confidence: {sc.get('confidence')}")
    mso = blob.get("myeongri_stream_outputs")
    if isinstance(mso, dict):
        lines.append(f"- myeongri_stream_outputs.state_id: {mso.get('state_id')}")
        rat = str(mso.get("rationale", ""))[:520]
        if rat:
            lines.append(f"- myeongri_stream_outputs.rationale (trim): {rat}")
    prov = blob.get("provenance")
    if isinstance(prov, dict):
        lines.append(f"- provenance.source: `{prov.get('source')}`")
    note = blob.get("note")
    if note:
        lines.append(f"- engine.note: {note}")
    return lines


def _disk_snapshot_lines_sasang(blob: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        f"- artifact.schema: `{blob.get('schema')}` version=`{blob.get('version')}` ts=`{blob.get('ts_utc')}`",
    ]
    sc = blob.get("scores")
    if isinstance(sc, dict):
        lines.append(f"- scores.direction_score: {sc.get('direction_score')}")
        lines.append(f"- scores.confidence: {sc.get('confidence')}")
    sso = blob.get("sasang_stream_outputs")
    if isinstance(sso, dict):
        lines.append(f"- sasang_stream_outputs.regime_hypothesis: `{sso.get('regime_hypothesis')}`")
        lines.append(f"- sasang_stream_outputs.mapping_target: `{sso.get('mapping_target')}`")
        rat = str(sso.get("rationale", ""))[:520]
        if rat:
            lines.append(f"- sasang_stream_outputs.rationale (trim): {rat}")
    prov = blob.get("provenance")
    if isinstance(prov, dict):
        lines.append(f"- provenance.source: `{prov.get('source')}`")
    note = blob.get("note")
    if note:
        lines.append(f"- engine.note: {note}")
    return lines


def _disk_snapshot_lines_logos(blob: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        f"- artifact.schema: `{blob.get('schema')}` version=`{blob.get('version')}` ts=`{blob.get('ts_utc')}`",
    ]
    sc = blob.get("scores")
    if isinstance(sc, dict):
        lines.append(f"- scores.direction_score: {sc.get('direction_score')}")
        lines.append(f"- scores.confidence: {sc.get('confidence')}")
    refs = blob.get("evidence_refs")
    if isinstance(refs, list):
        lines.append(f"- evidence_refs.count: {len(refs)}")
    nsg = blob.get("narrative_snippet_guarded")
    if isinstance(nsg, str) and nsg:
        lines.append(f"- narrative_snippet_guarded (trim): {nsg[:400]}")
    lso = blob.get("logos_stream_outputs")
    if isinstance(lso, dict):
        rat = str(lso.get("rationale", ""))[:520]
        if rat:
            lines.append(f"- logos_stream_outputs.rationale (trim): {rat}")
    prov = blob.get("provenance")
    if isinstance(prov, dict):
        lines.append(f"- provenance.source: `{prov.get('source')}`")
    note = blob.get("note")
    if note:
        lines.append(f"- engine.note: {note}")
    return lines


def disk_snapshot_lines(lens_id: str, blob: dict[str, Any]) -> list[str]:
    if lens_id == "myeongni":
        return _disk_snapshot_lines_myeongni(blob)
    if lens_id == "sasang":
        return _disk_snapshot_lines_sasang(blob)
    if lens_id == "logos":
        return _disk_snapshot_lines_logos(blob)
    return [f"- (no summarizer for lens_id={lens_id!r})"]


def stub_lens_workers(example: dict[str, Any]) -> list[dict[str, Any]]:
    """v0: return lens blocks from packaged example (no network / no engines)."""
    lenses = example.get("lenses")
    if not isinstance(lenses, list) or not lenses:
        raise ValueError("example.lenses must be a non-empty list")
    return copy.deepcopy(lenses)


def stub_coordinator_block(example: dict[str, Any]) -> dict[str, Any]:
    coord = example.get("coordinator")
    if not isinstance(coord, dict):
        raise ValueError("example.coordinator must be an object")
    return copy.deepcopy(coord)


def render_lens_slice_md(lens: dict[str, Any], disk_blob: dict[str, Any] | None) -> str:
    lid = str(lens.get("lens_id", "unknown"))
    mode_label = "stub + disk snapshot" if disk_blob is not None else "v0 stub / example-backed"
    lines: list[str] = [
        f"## Lens `{lid}` ({mode_label})",
        "",
    ]
    tags = lens.get("hypothesis_tags")
    if isinstance(tags, list) and tags:
        lines.append(f"- hypothesis_tags: {', '.join(str(t) for t in tags)}")
    eng = lens.get("engine_artifact_paths")
    if isinstance(eng, list) and eng:
        lines.append("- engine_artifact_paths:")
        for p in eng:
            lines.append(f"  - `{p}`")
    rag = lens.get("rag")
    corpus_id = ""
    if isinstance(rag, dict):
        corpus_id = str(rag.get("corpus_id", "") or "")
        lines.append(f"- rag.corpus_id: `{corpus_id}`")
        runs = rag.get("retrieval_runs")
        if isinstance(runs, list):
            for run in runs:
                if not isinstance(run, dict):
                    continue
                rid = run.get("run_id", "")
                q = str(run.get("query", ""))
                lines.append(f"  - run `{rid}` query: {q}")
                hits = run.get("hits")
                if isinstance(hits, list):
                    for hit in hits[:24]:
                        if not isinstance(hit, dict):
                            continue
                        sid = hit.get("source_id", "")
                        band = hit.get("confidence_band", "")
                        snip = str(hit.get("snippet", ""))[:400]
                        lines.append(f"    - `{sid}` band={band} snippet: {snip}")
    if disk_blob is not None:
        lines.append("")
        lines.append("### Disk engine snapshot (best-effort, independent-lens JSON)")
        lines.extend(disk_snapshot_lines(lid, disk_blob))
    lines.append("")
    if corpus_id == "premium_multilens_rag_offline_v1":
        lines.append(
            "_RAG hits above: offline keyword retrieval (`--rag-bundle`, `--rag-corpus-scan-dir`, or both); "
            "not live corpus or embedding search._"
        )
    else:
        lines.append(
            "_RAG rows above: schema-example stubs unless `--mode best-effort` with bundle and/or scan dir._"
        )
    lines.append("")
    return "\n".join(lines)


def render_synthesis_md(
    coordinator: dict[str, Any],
    lens_ids: list[str],
    disk_blobs: dict[str, dict[str, Any] | None] | None,
) -> str:
    lines: list[str] = [
        "## Coordinator synthesis (v0 structural join)",
        "",
        f"- coordinator_mode_label: `{coordinator.get('coordinator_mode_label', '')}`",
        f"- lens_order: {', '.join(lens_ids)}",
        "",
    ]
    if disk_blobs:
        rows: list[str] = []
        for lid in lens_ids:
            b = disk_blobs.get(lid)
            if not isinstance(b, dict):
                rows.append(f"| `{lid}` | (no disk) | (no disk) |")
                continue
            sc = b.get("scores") if isinstance(b.get("scores"), dict) else {}
            d = sc.get("direction_score")
            c = sc.get("confidence")
            rows.append(f"| `{lid}` | {d} | {c} |")
        if any("no disk" not in r for r in rows):
            lines.append("### Numeric alignment (disk `scores`, B-track)")
            lines.append("")
            lines.append("| lens | direction_score | confidence |")
            lines.append("| --- | ---: | ---: |")
            lines.extend(rows)
            lines.append("")
    conflicts = coordinator.get("conflicts")
    if isinstance(conflicts, list):
        for row in conflicts:
            if not isinstance(row, dict):
                continue
            topic = row.get("topic", "")
            lines.append(f"### Conflict: {topic}")
            for k in ("myeongni_note", "sasang_note", "logos_note"):
                v = row.get(k)
                if v:
                    lines.append(f"- {k}: {v}")
            res = row.get("resolution_advisory", "")
            if res:
                lines.append(f"- **resolution_advisory**: {res}")
            lines.append("")
    caveats = coordinator.get("caveats")
    if isinstance(caveats, list) and caveats:
        lines.append("### Caveats")
        for c in caveats:
            lines.append(f"- {c}")
        lines.append("")
    return "\n".join(lines)


def _load_shock_ablation_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def render_shock_ablation_md(doc: dict[str, Any]) -> str:
    """Render 3-arm soft hit rates table from shock ablation artifact."""
    arms = doc.get("arms") if isinstance(doc.get("arms"), dict) else {}
    arm_order = ("active", "fusion_always", "fusion_shock_only")
    lines: list[str] = [
        "> `[HYPO]` · B-track · `send_gate: HOLD` · research_only",
        "",
        "| arm | n_scored | shock_days | soft_hit_rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for aid in arm_order:
        arm = arms.get(aid) if isinstance(arms.get(aid), dict) else {}
        n = arm.get("n_scored", "—")
        shock_n = arm.get("shock_days", "—")
        rate = arm.get("soft_hit_rate")
        rate_s = f"{float(rate):.4f}" if rate is not None else "—"
        lines.append(f"| `{aid}` | {n} | {shock_n} | {rate_s} |")
    comp = doc.get("comparison") if isinstance(doc.get("comparison"), dict) else {}
    thresholds = doc.get("shock_thresholds") if isinstance(doc.get("shock_thresholds"), dict) else {}
    lines.extend(
        [
            "",
            f"- **delta_shock_only_minus_active**: {comp.get('delta_shock_only_minus_active', '—')}",
            f"- **delta_always_minus_active**: {comp.get('delta_always_minus_active', '—')}",
            f"- **promotion_candidate**: `{doc.get('promotion_candidate')}`",
            f"- **verdict_ko**: {doc.get('verdict_ko', '—')}",
        ]
    )
    if thresholds:
        lines.append(
            f"- shock thresholds: |return|>={thresholds.get('abs_return_pct')}% · prior<={thresholds.get('prior_kospi_pct')}%"
        )
    lines.append("")
    return "\n".join(lines)


def render_field_band_stack_md(doc: dict[str, Any]) -> str:
    """Thin slice: Field band conformal stack (vol-widen + RWC/CPTC union) [HYPO]."""
    stack = doc.get("stack") if isinstance(doc.get("stack"), dict) else doc
    hold_base = stack.get("holdout_band_base")
    hold_rwc = stack.get("holdout_band_rwc")
    hold_cptc = stack.get("holdout_band_cptc")
    hold_union = stack.get("holdout_band_stack_union") or stack.get("holdout_band_stack")
    lines: list[str] = [
        "> `[HYPO]` · B-track · `send_gate: HOLD` · band layer only · direction unchanged",
        "",
        "| layer | holdout band_hit_rate |",
        "| --- | ---: |",
        f"| baseline (vol-widen) | {hold_base if hold_base is not None else '—'} |",
        f"| RWC-lite | {hold_rwc if hold_rwc is not None else '—'} |",
        f"| CPTC-lite | {hold_cptc if hold_cptc is not None else '—'} |",
        f"| stack_union | {hold_union if hold_union is not None else '—'} |",
        "",
        f"- **best_band_layer**: `{stack.get('best_band_layer', '—')}`",
        f"- **finstress_recommendation**: `{stack.get('finstress_recommendation', '—')}`",
        f"- **l3_ack_ready**: `{stack.get('l3_ack_ready', '—')}`",
        "",
        "_Not PnL·not live inject·science_core backfill rows may apply in extended panel._",
        "",
    ]
    return "\n".join(lines)


def render_package_md(
    report: dict[str, Any],
    slice_contents: dict[str, str],
    synthesis_text: str,
    *,
    mode: Mode,
    four_lens_fusion_section: str | None = None,
    shock_ablation_section: str | None = None,
    shock_fusion_wf_section: str | None = None,
    field_band_stack_section: str | None = None,
) -> str:
    tw = report.get("track_wall", [])
    tw_s = ", ".join(str(x) for x in tw) if isinstance(tw, list) else str(tw)
    ns = report.get("non_scope_ack", {})
    lines: list[str] = [
        "<!-- premium_btrack_multilens_report_v0 -->",
        "",
        f"# Premium B-track multi-lens report ({'v0.5 best-effort disk' if mode == 'best-effort' else 'v0 stub'})",
        "",
        "> **Track**: B-track research / `[HYPO]`",
        f"> **track_wall**: `{tw_s}`",
        "",
        "## Fact-Lock banner (non_scope_ack)",
        "",
        f"- not_clinical_diagnosis: `{ns.get('not_clinical_diagnosis')}`",
        f"- not_live_trading: `{ns.get('not_live_trading')}`",
        f"- not_regime_autotrigger: `{ns.get('not_regime_autotrigger')}`",
        f"- logos_non_gating: `{ns.get('logos_non_gating')}`",
        "",
        "---",
        "",
        "## Per-lens slices (embedded for v0 single-file review)",
        "",
    ]
    for lid, body in slice_contents.items():
        lines.append(f"<a id=\"lens-{lid}\"></a>")
        lines.append(body)
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## Coordinator bundle")
    lines.append("")
    lines.append(synthesis_text)
    lines.append("")
    if four_lens_fusion_section:
        lines.append("---")
        lines.append("")
        lines.append("## Four-lens GraphRAG fusion (KOSPI PoC)")
        lines.append("")
        lines.append(four_lens_fusion_section)
        lines.append("")
    if shock_ablation_section:
        lines.append("---")
        lines.append("")
        lines.append("## Shock-conditional fusion ablation")
        lines.append("")
        lines.append(shock_ablation_section)
        lines.append("")
    if shock_fusion_wf_section:
        lines.append("---")
        lines.append("")
        lines.append("## Shock-day-only fusion walkforward (KOSPI June 2026)")
        lines.append("")
        lines.append(shock_fusion_wf_section)
        lines.append("")
    if field_band_stack_section:
        lines.append("---")
        lines.append("")
        lines.append("## Field band conformal stack (late conditioning)")
        lines.append("")
        lines.append(field_band_stack_section)
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Disclaimers")
    lines.append("")
    dis = report.get("disclaimers")
    if isinstance(dis, list):
        for d in dis:
            lines.append(f"- {d}")
    lines.append("")
    lines.append("---")
    lines.append("")
    if mode == "best-effort":
        lines.append(
            "_End of report. v0.5: independent-lens JSON on disk merged into MD; "
            "RAG/API workers and async queue still TBD._"
        )
    else:
        lines.append("_End of report. v0 uses example-backed RAG stubs; replace workers incrementally._")
    lines.append("")
    return "\n".join(lines)


def _maybe_validate(instance: dict[str, Any], schema_path: Path) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        print("WARN: jsonschema not installed; skip schema validation.", file=sys.stderr)
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)


def _build_async_job_payload(*, async_job_id: str | None, async_simulate: bool) -> dict[str, Any] | None:
    """Optional queue-shaped handoff for the sync builder (no worker attached)."""
    if not async_simulate and not (async_job_id and str(async_job_id).strip()):
        return None
    queued = _utc_z()
    if async_job_id and str(async_job_id).strip():
        raw = str(async_job_id).strip()
        job_id = raw[:128]
        if len(job_id) < 8:
            job_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        return {
            "job_id": job_id,
            "status": "queued",
            "queued_at_utc": queued,
            "note": "async_job from --async-job-id; sync builder only — attach worker separately.",
        }
    digest = hashlib.sha256(queued.encode("utf-8")).hexdigest()[:16]
    return {
        "job_id": f"sim_premium_{digest}",
        "status": "queued",
        "queued_at_utc": queued,
        "note": "Simulated handoff (--async-simulate); no queue worker in sync v0.",
    }


def _insert_best_effort_caveat(
    *,
    mode: Mode,
    coord: dict[str, Any],
    lenses: list[dict[str, Any]],
    disk_blobs: dict[str, dict[str, Any] | None],
    rag_offline_note: str | None = None,
) -> None:
    if mode != "best-effort":
        return
    trace_parts: list[str] = []
    for lens in lenses:
        if not isinstance(lens, dict):
            continue
        lid = str(lens.get("lens_id", ""))
        if (disk_blobs or {}).get(lid) is None:
            trace_parts.append(f"{lid}=MISSING")
            continue
        paths = lens.get("engine_artifact_paths")
        if isinstance(paths, list) and paths:
            trace_parts.append(f"{lid}={' '.join(str(p) for p in paths)}")
        else:
            trace_parts.append(f"{lid}=LOADED_NO_PATH")
    line = "Fact-Lock trace (best-effort disk ingest): " + " | ".join(trace_parts)
    if len(line) > 1950:
        line = line[:1947] + "..."
    caveats = coord.get("caveats")
    if not isinstance(caveats, list):
        caveats = []
        coord["caveats"] = caveats
    caveats.insert(0, line)
    if rag_offline_note:
        rag_line = (
            f"RAG (offline keyword, B-track): {rag_offline_note} — "
            "not neural/API RAG; ranked by token overlap with disk lens blob text."
        )
        if len(rag_line) > 1950:
            rag_line = rag_line[:1947] + "..."
        caveats.insert(1, rag_line)


def _finalize_pipeline_outputs(
    pipeline: list[Any],
    *,
    mode: Mode,
    root: Path,
    slice_paths: dict[str, Path],
    synthesis_path: Path,
    main_json_path: Path,
    main_md_path: Path,
) -> None:
    """Point pipeline steps at real on-disk outputs; step 1 script_ref gets mode tag in best-effort."""
    if not isinstance(pipeline, list):
        return

    owner_outputs: dict[str, list[str]] = {}
    for lid, pth in slice_paths.items():
        owner_outputs[lid] = [_posix_under_root(pth, root)]
    owner_outputs["coordinator"] = [_posix_under_root(synthesis_path, root)]

    for step in pipeline:
        if not isinstance(step, dict):
            continue
        own = step.get("owner")
        if own in owner_outputs:
            step["outputs"] = list(owner_outputs[str(own)])
        if mode == "best-effort" and step.get("step") == 1 and own == "orchestrator":
            prev = str(step.get("script_ref", "")).strip()
            tag = " [actual_mode=best-effort]"
            merged = (prev + tag).strip()
            if len(merged) > 1024:
                merged = merged[:1021] + "..."
            step["script_ref"] = merged

        outs = step.get("outputs")
        if not isinstance(outs, list):
            continue
        new_outs: list[str] = []
        for o in outs:
            if isinstance(o, str) and o.endswith("premium_btrack_multilens_report_v1.json"):
                new_outs.append(_posix_under_root(main_json_path, root))
            elif isinstance(o, str) and o.endswith("premium_btrack_multilens_report_v1.md"):
                new_outs.append(_posix_under_root(main_md_path, root))
            else:
                new_outs.append(str(o))
        step["outputs"] = new_outs


def build_report(
    *,
    root: Path,
    out_dir: Path,
    example_path: Path,
    validate_schema: bool,
    mode: Mode = "stub",
    artifact_overrides: dict[str, Path] | None = None,
    rag_bundle_path: Path | None = None,
    rag_corpus_scan_dir: Path | None = None,
    async_simulate: bool = False,
    async_job_id: str | None = None,
    async_queue_enqueue: bool = False,
    async_queue_path: Path | None = None,
    four_lens_fusion_md: Path | None = None,
    shock_ablation_json: Path | None = None,
    shock_fusion_wf_md: Path | None = None,
    field_band_stack_json: Path | None = None,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    main_md_path = out_dir / "premium_btrack_multilens_report_v1.md"
    main_json_path = out_dir / "premium_btrack_multilens_report_v1.json"

    example = _load_example(example_path)
    lenses = stub_lens_workers(example)
    coord = stub_coordinator_block(example)

    overrides = artifact_overrides or {}
    disk_blobs = attach_disk_engine_paths(root=root, lenses=lenses, mode=mode, overrides=overrides)

    scan_dir = rag_corpus_scan_dir
    if scan_dir is not None and not scan_dir.is_absolute():
        scan_dir = (root / scan_dir).resolve()
    if scan_dir is not None and not scan_dir.is_dir():
        print(f"WARN: --rag-corpus-scan-dir not a directory, skipping scan: {scan_dir}", file=sys.stderr)
        scan_dir = None

    rag_offline_note = enrich_lenses_rag_offline(
        mode=mode,
        root=root,
        lenses=lenses,
        disk_blobs=disk_blobs,
        bundle_path=rag_bundle_path,
        scan_dir=scan_dir,
    )
    _insert_best_effort_caveat(
        mode=mode,
        coord=coord,
        lenses=lenses,
        disk_blobs=disk_blobs,
        rag_offline_note=rag_offline_note,
    )

    lens_ids = [str(x.get("lens_id", "")) for x in lenses if isinstance(x, dict)]

    slice_paths: dict[str, Path] = {}
    slice_contents: dict[str, str] = {}
    for lens in lenses:
        if not isinstance(lens, dict):
            continue
        lid = str(lens.get("lens_id", "unknown"))
        blob = disk_blobs.get(lid) if disk_blobs else None
        body = render_lens_slice_md(lens, blob)
        slice_contents[lid] = body
        p = out_dir / f"lens_{lid}_premium_slice_v0.md"
        p.write_text(body, encoding="utf-8")
        slice_paths[lid] = p
        if lens.get("sections") and isinstance(lens["sections"], list) and lens["sections"]:
            sec0 = lens["sections"][0]
            if isinstance(sec0, dict):
                sec0["markdown_path"] = _posix_under_root(p, root)

    synthesis_path = out_dir / "premium_multilens_synthesis_v0.md"
    synthesis_text = render_synthesis_md(coord, lens_ids, disk_blobs if mode == "best-effort" else None)
    synthesis_path.write_text(synthesis_text, encoding="utf-8")
    coord["synthesis_markdown_path"] = _posix_under_root(synthesis_path, root)

    fusion_section: str | None = None
    fusion_attach: str | None = None
    if four_lens_fusion_md is not None and four_lens_fusion_md.is_file():
        fusion_section = four_lens_fusion_md.read_text(encoding="utf-8")
        fusion_attach = _posix_under_root(four_lens_fusion_md, root)
        caveats = coord.get("caveats")
        if not isinstance(caveats, list):
            caveats = []
            coord["caveats"] = caveats
        caveats.append(f"four_lens_fusion_attached: {fusion_attach} [HYPO·NON_GATING]")

    shock_section: str | None = None
    shock_ablation_attach: str | None = None
    if shock_ablation_json is not None and shock_ablation_json.is_file():
        shock_doc = _load_shock_ablation_json(shock_ablation_json)
        if shock_doc:
            shock_section = render_shock_ablation_md(shock_doc)
            shock_ablation_attach = _posix_under_root(shock_ablation_json, root)
            caveats = coord.get("caveats")
            if not isinstance(caveats, list):
                caveats = []
                coord["caveats"] = caveats
            caveats.append(f"shock_ablation_attached: {shock_ablation_attach} [HYPO·NON_GATING]")

    shock_wf_section: str | None = None
    shock_wf_attach: str | None = None
    if shock_fusion_wf_md is not None and shock_fusion_wf_md.is_file():
        shock_wf_section = shock_fusion_wf_md.read_text(encoding="utf-8")
        shock_wf_attach = _posix_under_root(shock_fusion_wf_md, root)
        caveats = coord.get("caveats")
        if not isinstance(caveats, list):
            caveats = []
            coord["caveats"] = caveats
        caveats.append(f"shock_fusion_wf_attached: {shock_wf_attach} [HYPO·research_only]")

    field_band_section: str | None = None
    field_band_attach: str | None = None
    if field_band_stack_json is not None and field_band_stack_json.is_file():
        fb_doc = _load_shock_ablation_json(field_band_stack_json)
        if fb_doc:
            field_band_section = render_field_band_stack_md(fb_doc)
            field_band_attach = _posix_under_root(field_band_stack_json, root)
            caveats = coord.get("caveats")
            if not isinstance(caveats, list):
                caveats = []
                coord["caveats"] = caveats
            caveats.append(f"field_band_stack_attached: {field_band_attach} [HYPO·band_only·NON_GATING]")

    report = copy.deepcopy(example)
    report["generated_at_utc"] = _utc_z()
    report.pop("async_job", None)
    aj = _build_async_job_payload(async_job_id=async_job_id, async_simulate=async_simulate)
    if aj is not None:
        report["async_job"] = aj
    report["lenses"] = lenses
    report["coordinator"] = coord

    package_md = render_package_md(
        report,
        slice_contents,
        synthesis_text,
        mode=mode,
        four_lens_fusion_section=fusion_section,
        shock_ablation_section=shock_section,
        shock_fusion_wf_section=shock_wf_section,
        field_band_stack_section=field_band_section,
    )
    main_md_path.write_text(package_md, encoding="utf-8")
    md_hash = _sha256_bytes(main_md_path.read_bytes())

    pkg_art: dict[str, Any] = {
        "report_json_path": _posix_under_root(main_json_path, root),
        "report_markdown_path": _posix_under_root(main_md_path, root),
        "manifest_sha256": md_hash,
    }
    attachments: list[str] = []
    if fusion_attach:
        attachments.append(fusion_attach)
    if shock_ablation_attach:
        attachments.append(shock_ablation_attach)
    if shock_wf_attach:
        attachments.append(shock_wf_attach)
    if field_band_attach:
        attachments.append(field_band_attach)
    if attachments:
        pkg_art["attachments"] = attachments
    report["package_artifacts"] = pkg_art

    pl = report.get("pipeline")
    if isinstance(pl, list):
        _finalize_pipeline_outputs(
            pl,
            mode=mode,
            root=root,
            slice_paths=slice_paths,
            synthesis_path=synthesis_path,
            main_json_path=main_json_path,
            main_md_path=main_md_path,
        )

    main_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if async_queue_enqueue:
        aj = report.get("async_job")
        if not isinstance(aj, dict) or not str(aj.get("job_id", "")).strip():
            print(
                "WARN: --async-queue-enqueue skipped (async_job missing or empty job_id); "
                "use --async-simulate and/or --async-job-id.",
                file=sys.stderr,
            )
        else:
            qp = async_queue_path
            if qp is None:
                qp = (root / "reports" / "premium_multilens_job_queue_v0.jsonl").resolve()
            else:
                qp = qp.resolve() if qp.is_absolute() else (root / qp).resolve()
            try:
                mod = _load_premium_multilens_queue_stub_v1()
                ent = mod.build_queue_entry_v0(
                    job_id=str(aj["job_id"]),
                    queued_at_utc=str(aj.get("queued_at_utc") or _utc_z()),
                    status=str(aj.get("status") or "queued"),
                    report_json_path=main_json_path,
                    mode=mode,
                    root=root,
                )
                mod.append_queue_line_v0(qp, ent)
                print(f"OK: queue append {_posix_under_root(qp, root)}")
            except Exception as exc:  # noqa: BLE001 — best-effort enqueue must not fail the packager
                print(f"WARN: queue stub append failed: {exc}", file=sys.stderr)

    schema_path = root / "docs" / "final" / "schemas" / "premium_btrack_multilens_report_v1.schema.json"
    if validate_schema:
        _maybe_validate(report, schema_path)

    print(f"OK: wrote {_posix_under_root(main_md_path, root)}")
    print(f"OK: wrote {_posix_under_root(main_json_path, root)}")
    return 0


def main() -> int:
    root = _repo_root()
    default_example = root / "docs" / "final" / "schemas" / "premium_btrack_multilens_report_v1.example.json"
    default_out = root / "reports"

    ap = argparse.ArgumentParser(description="Build premium B-track multi-lens report package (v0 stub).")
    ap.add_argument("--out-dir", type=Path, default=default_out, help="Output directory (default: reports/)")
    ap.add_argument("--example-path", type=Path, default=default_example, help="Stub source JSON (default: schema example)")
    ap.add_argument(
        "--mode",
        choices=("stub", "best-effort"),
        default="stub",
        help="stub=example only; best-effort=attach independent-lens JSON from disk (defaults under docs/final/artifacts/).",
    )
    ap.add_argument("--myeongni-json", type=Path, default=None, help="Override myeongni independent-lens JSON path")
    ap.add_argument("--sasang-json", type=Path, default=None, help="Override sasang independent-lens JSON path")
    ap.add_argument("--logos-json", type=Path, default=None, help="Override logos independent-lens JSON path")
    ap.add_argument(
        "--rag-bundle",
        type=Path,
        default=None,
        help="Offline keyword RAG corpus bundle JSON (default: tests/fixtures/premium_multilens_rag_corpus_bundle_v1.json if present).",
    )
    ap.add_argument(
        "--rag-corpus-scan-dir",
        type=Path,
        default=None,
        help="Optional directory of .txt/.md/.json excerpts merged into offline RAG (best-effort).",
    )
    ap.add_argument(
        "--async-simulate",
        action="store_true",
        help="Emit schema async_job with queued status (sync builder placeholder; no worker).",
    )
    ap.add_argument(
        "--async-job-id",
        type=str,
        default=None,
        help="Use this job_id in async_job (min 8 chars recommended; shorter values are hashed).",
    )
    ap.add_argument(
        "--async-queue-enqueue",
        action="store_true",
        help="When async_job is present, append one JSONL line via premium_multilens_job_queue_stub_v1 (v0 file queue).",
    )
    ap.add_argument(
        "--async-queue-path",
        type=Path,
        default=None,
        help="Queue JSONL path (default: reports/premium_multilens_job_queue_v0.jsonl under workspace root).",
    )
    ap.add_argument("--no-validate", action="store_true", help="Skip jsonschema validation when available")
    ap.add_argument(
        "--four-lens-fusion-md",
        type=Path,
        default=None,
        help="Attach KOSPI four-lens GraphRAG fusion markdown section (best-effort default if present).",
    )
    ap.add_argument(
        "--shock-ablation-json",
        type=Path,
        default=None,
        help="Shock-conditional fusion ablation JSON for premium report section (best-effort default if present).",
    )
    ap.add_argument(
        "--shock-fusion-wf-md",
        type=Path,
        default=None,
        help="Shock-day-only fusion walkforward markdown section for premium report.",
    )
    ap.add_argument(
        "--field-band-stack-json",
        type=Path,
        default=None,
        help="Field band stack_compare JSON for premium report section (best-effort default if present).",
    )
    args = ap.parse_args()

    out_dir = args.out_dir
    if not out_dir.is_absolute():
        out_dir = (root / out_dir).resolve()

    example_path = args.example_path
    if not example_path.is_absolute():
        example_path = (root / example_path).resolve()

    if not example_path.is_file():
        print(f"ERROR: example not found: {example_path}", file=sys.stderr)
        return 2

    overrides: dict[str, Path] = {}
    for key, arg in (
        ("myeongni", args.myeongni_json),
        ("sasang", args.sasang_json),
        ("logos", args.logos_json),
    ):
        if arg is None:
            continue
        p = Path(arg)
        if not p.is_absolute():
            p = (root / p).resolve()
        overrides[key] = p

    mode: Mode = "best-effort" if args.mode == "best-effort" else "stub"

    rag_bundle: Path | None = None
    if args.rag_bundle is not None:
        rb = Path(args.rag_bundle)
        if not rb.is_absolute():
            rb = (root / rb).resolve()
        rag_bundle = rb if rb.is_file() else None
        if args.rag_bundle is not None and rag_bundle is None:
            print(f"WARN: --rag-bundle not found, skipping offline RAG: {rb}", file=sys.stderr)
    else:
        cand = root / "tests" / "fixtures" / "premium_multilens_rag_corpus_bundle_v1.json"
        if cand.is_file():
            rag_bundle = cand

    scan_arg = args.rag_corpus_scan_dir
    rag_scan: Path | None = None
    if scan_arg is not None:
        rs = Path(scan_arg)
        if not rs.is_absolute():
            rs = (root / rs).resolve()
        rag_scan = rs

    fusion_md: Path | None = None
    if args.four_lens_fusion_md is not None:
        fp = Path(args.four_lens_fusion_md)
        if not fp.is_absolute():
            fp = (root / fp).resolve()
        fusion_md = fp if fp.is_file() else None
    elif mode == "best-effort":
        cand_f = root / "reports" / "kospi_four_lens_graphrag_fusion_v1_latest.md"
        if cand_f.is_file():
            fusion_md = cand_f

    shock_json: Path | None = None
    if args.shock_ablation_json is not None:
        sp = Path(args.shock_ablation_json)
        if not sp.is_absolute():
            sp = (root / sp).resolve()
        shock_json = sp if sp.is_file() else None
    elif mode == "best-effort":
        cand_s = root / "reports" / "kospi_four_lens_shock_conditional_ablation_v1_latest.json"
        if cand_s.is_file():
            shock_json = cand_s

    shock_wf_md: Path | None = None
    if args.shock_fusion_wf_md is not None:
        wp = Path(args.shock_fusion_wf_md)
        if not wp.is_absolute():
            wp = (root / wp).resolve()
        shock_wf_md = wp if wp.is_file() else None
    elif mode == "best-effort":
        cand_w = root / "reports" / "kospi_four_lens_shock_fusion_walkforward_v1_latest.md"
        if cand_w.is_file():
            shock_wf_md = cand_w

    field_band_json: Path | None = None
    if args.field_band_stack_json is not None:
        bp = Path(args.field_band_stack_json)
        if not bp.is_absolute():
            bp = (root / bp).resolve()
        field_band_json = bp if bp.is_file() else None
    elif mode == "best-effort":
        cand_b = root / "reports" / "kospi_field_band_stack_compare_v1_latest.json"
        if cand_b.is_file():
            field_band_json = cand_b

    return build_report(
        root=root,
        out_dir=out_dir,
        example_path=example_path,
        validate_schema=not args.no_validate,
        mode=mode,
        artifact_overrides=overrides or None,
        rag_bundle_path=rag_bundle,
        rag_corpus_scan_dir=rag_scan,
        async_simulate=bool(args.async_simulate),
        async_job_id=(str(args.async_job_id).strip() if args.async_job_id else None),
        async_queue_enqueue=bool(args.async_queue_enqueue),
        async_queue_path=(Path(args.async_queue_path) if args.async_queue_path else None),
        four_lens_fusion_md=fusion_md,
        shock_ablation_json=shock_json,
        shock_fusion_wf_md=shock_wf_md,
        field_band_stack_json=field_band_json,
    )


if __name__ == "__main__":
    raise SystemExit(main())
