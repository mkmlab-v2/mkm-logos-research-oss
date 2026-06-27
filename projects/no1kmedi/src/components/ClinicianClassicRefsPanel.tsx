"use client";

export type KmClassicCitationV1 = {
  source_id: string;
  work: string;
  chapter?: string | null;
  relative_path?: string;
  excerpt_hash?: string | null;
  retrieval_query: string;
  citation_valid: boolean;
};

type ClinicianClassicRefsPanelProps = {
  refs: KmClassicCitationV1[];
  /** When true, show physician-only notice (default). */
  physicianOnly?: boolean;
};

export function ClinicianClassicRefsPanel({
  refs,
  physicianOnly = true,
}: ClinicianClassicRefsPanelProps) {
  if (!refs.length) return null;

  return (
    <details className="clinician-classic-refs" open={false}>
      <summary className="clinician-classic-refs-summary">
        <span className="clinician-classic-refs-tag">[FACT]</span> 한의 원전 인용 ({refs.length})
      </summary>
      {physicianOnly ? (
        <p className="workspace-muted clinician-classic-refs-note">
          원장 검토 초안 · read-only citation · 환자 기본 화면에 노출하지 않음 · raw_converted — 원문 대조 필수
        </p>
      ) : null}
      <ul className="clinician-classic-refs-list">
        {refs.map((ref) => (
          <li key={`${ref.source_id}-${ref.retrieval_query}`}>
            <article className="card citation-card clinician-classic-ref-card">
              <h4>
                {ref.work}{" "}
                <code className="clinician-classic-ref-id">{ref.source_id}</code>
                {ref.citation_valid ? (
                  <span className="clinician-classic-refs-tag">[FACT]</span>
                ) : (
                  <span className="clinician-classic-refs-tag clinician-classic-refs-tag--warn">[INVALID]</span>
                )}
              </h4>
              {ref.relative_path ? (
                <p className="consult-source-chip">
                  <strong>path:</strong> {ref.relative_path}
                </p>
              ) : null}
              <p className="workspace-muted">
                <strong>query:</strong> {ref.retrieval_query}
              </p>
            </article>
          </li>
        ))}
      </ul>
    </details>
  );
}
