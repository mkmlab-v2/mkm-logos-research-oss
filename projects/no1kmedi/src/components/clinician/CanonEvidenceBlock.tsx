export type CanonEvidenceChunk = {
  chunk_id: string;
  preview_80chars?: string;
  section_label?: string;
};

type CanonEvidenceBlockProps = {
  chunks: CanonEvidenceChunk[];
  emptyHint?: string;
};

/** Pack F — excerpt first, chunk_id secondary (collapsed when empty). */
export function CanonEvidenceBlock({ chunks, emptyHint }: CanonEvidenceBlockProps) {
  if (chunks.length === 0) {
    return (
      <div className="canon-evidence-block canon-evidence-block--empty">
        <p className="canon-evidence-empty">
          {emptyHint || "CDS envelope 연결 후 표시 · 또는 원전 검색"}
        </p>
      </div>
    );
  }

  return (
    <details className="canon-evidence-block" open={chunks.length <= 3}>
      <summary className="canon-evidence-header">
        원전 근거 ({chunks.length}) <span className="canon-evidence-badge">[교육·문화]</span>
      </summary>
      <ul className="canon-evidence-list">
        {chunks.slice(0, 3).map((c) => (
          <li key={c.chunk_id}>
            {c.section_label ? <p className="canon-evidence-section">{c.section_label}</p> : null}
            <p className="canon-evidence-excerpt">{c.preview_80chars || "—"}</p>
            <code className="canon-evidence-id">{c.chunk_id}</code>
          </li>
        ))}
      </ul>
    </details>
  );
}
