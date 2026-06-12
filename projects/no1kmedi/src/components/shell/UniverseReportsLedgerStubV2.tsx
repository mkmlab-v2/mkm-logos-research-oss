import type { UniverseHubReportLedgerStubV1 } from "@/lib/universeHubReportLedgerStubV1";

type Props = {
  ledger: UniverseHubReportLedgerStubV1;
};

function formatUtc(iso: string): string {
  try {
    return new Date(iso).toISOString().slice(0, 10);
  } catch {
    return iso;
  }
}

export function UniverseReportsLedgerStubV2({ ledger }: Props) {
  return (
    <section className="universe-hub-ledger-stub" aria-labelledby="hub-ledger-stub-heading">
      <h2 id="hub-ledger-stub-heading" className="universe-hub-section-title">
        허브 장부 미리보기 (stub)
      </h2>
      <p className="universe-hub-section-lead">{ledger.disclaimer_ko}</p>
      <p className="universe-hub-ledger-meta">
        <span className="universe-hub-compliance-tag">{ledger.hypothesis_tag}</span>
        <span className="universe-hub-compliance-tag">stub only</span>
        <time dateTime={ledger.last_updated_utc}>갱신 {formatUtc(ledger.last_updated_utc)}</time>
      </p>
      <div className="universe-hub-package-table-wrap">
        <table className="universe-hub-package-table">
          <thead>
            <tr>
              <th scope="col">제목</th>
              <th scope="col">레인</th>
              <th scope="col">상태</th>
              <th scope="col">갱신</th>
            </tr>
          </thead>
          <tbody>
            {ledger.entries.map((row) => (
              <tr key={row.id}>
                <td>{row.title_ko}</td>
                <td>
                  <code className="universe-hub-artifact-path">{row.lane}</code>
                </td>
                <td>{row.status}</td>
                <td>
                  <time dateTime={row.updated_utc}>{formatUtc(row.updated_utc)}</time>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
