"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CanonEvidenceBlock } from "@/components/clinician/CanonEvidenceBlock";

type CanonChunk = {
  chunk_id: string;
  preview_80chars?: string;
  section_label?: string;
  line_start?: number;
  line_end?: number;
};

type CanonCiteResponse = {
  success: boolean;
  error?: string;
  chunks?: CanonChunk[];
  disclaimer_ko?: string;
  philosophy_hypo_note_ko?: string;
};

type ClinicianCanonCitePanelProps = {
  suggestedQuery?: string;
};

export function ClinicianCanonCitePanel({ suggestedQuery = "" }: ClinicianCanonCitePanelProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(suggestedQuery);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [chunks, setChunks] = useState<CanonChunk[]>([]);
  const [disclaimer, setDisclaimer] = useState("");
  const userEditedRef = useRef(false);
  const lastAutoQueryRef = useRef("");

  const search = useCallback(async (text: string) => {
    const q = text.trim();
    if (q.length < 2) return;
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`/api/clinician/canon-cite-v1?q=${encodeURIComponent(q)}&limit=3`);
      const json = (await res.json()) as CanonCiteResponse;
      if (!res.ok || !json.success) {
        throw new Error(json.error || "canon_cite_failed");
      }
      setChunks(json.chunks || []);
      setDisclaimer(json.disclaimer_ko || "");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "lookup_failed";
      setError(msg);
      setChunks([]);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    const next = suggestedQuery.trim();
    if (!next) return;
    if (userEditedRef.current && query.trim() && query.trim() !== lastAutoQueryRef.current) return;
    lastAutoQueryRef.current = next;
    setQuery(next);
  }, [suggestedQuery, query]);

  useEffect(() => {
    const q = suggestedQuery.trim();
    if (!open || q.length < 2) return;
    if (q === lastAutoQueryRef.current && chunks.length > 0) return;
    const t = window.setTimeout(() => {
      void search(q);
    }, 400);
    return () => window.clearTimeout(t);
  }, [open, suggestedQuery, search, chunks.length]);

  return (
    <aside
      className={`clinician-canon-cite-panel${open ? " is-open" : ""}`}
      aria-label="원전 참고"
    >
      <button
        type="button"
        className="clinician-canon-cite-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "원전 참고 닫기" : "원전 참고 [교육·문화]"}
      </button>
      {open ? (
        <div className="clinician-canon-cite-sheet">
          <div className="clinician-canon-cite-body notice-box">
            <p className="clinician-canon-cite-hypo">
              [HYPO] 함억·두견 등 철학 맥락은 보조 참고만 — 체질 라벨·처방 트리거 아님.
            </p>
            {suggestedQuery.trim() ? (
              <p className="clinician-canon-cite-prefill" role="status">
                CDS·주증상 기반 제안: {suggestedQuery.trim().slice(0, 60)}
                {suggestedQuery.trim().length > 60 ? "…" : ""}
              </p>
            ) : null}
            <form
              className="clinician-canon-cite-form"
              onSubmit={(e) => {
                e.preventDefault();
                void search(query);
              }}
            >
              <input
                type="search"
                value={query}
                onChange={(e) => {
                  userEditedRef.current = true;
                  setQuery(e.target.value);
                }}
                placeholder="예: 소화 불량, 太陽, 補瀉"
                aria-label="원전 검색"
                disabled={busy}
              />
              <button type="submit" disabled={busy || query.trim().length < 2}>
                {busy ? "검색 중…" : "cite"}
              </button>
            </form>
            {error ? (
              <p className="clinician-canon-cite-error" role="alert">
                {error}
              </p>
            ) : null}
            <CanonEvidenceBlock chunks={chunks} />
            {disclaimer ? <p className="clinician-canon-cite-foot">{disclaimer}</p> : null}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
