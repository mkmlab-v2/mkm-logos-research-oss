import { logosResearchCopy } from "@/content/logosResearchCopy";

export function LogosResearchFooter() {
  const c = logosResearchCopy;
  const footer = "footer" in c && c.footer ? c.footer : null;
  const publicHost = c.publicUrl.replace(/^https?:\/\//, "");

  return (
    <footer className="lr-footer">
      <div className="lr-footer-inner">
        <p className="lr-footer-brand">
          {c.brand.productShort} · {c.brand.productLine}
        </p>
        <p className="lr-footer-meta">
          <a href={c.publicUrl}>{publicHost}</a>
        </p>
        <nav className="lr-footer-links" aria-label="LOGOS research footer">
          <a href="/logos-research/ask">베타 Q&A</a>
          <a href="/logos-research/docs">문서</a>
          <a href="/logos-research/studio" title="베타 후 · OSS 검증 후">
            Studio
          </a>
          {footer?.hub ? (
            <a href={footer.hub} rel="noopener noreferrer">
              {footer.hub_label ?? "JEMA AI 허브"}
            </a>
          ) : null}
        </nav>
        <p className="lr-footer-legal">{c.brand.legal}</p>
      </div>
    </footer>
  );
}
