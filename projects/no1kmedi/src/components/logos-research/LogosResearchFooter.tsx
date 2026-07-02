import { logosResearchCopy } from "@/content/logosResearchCopy";

export function LogosResearchFooter() {
  const c = logosResearchCopy;
  const footer = "footer" in c && c.footer ? c.footer : null;

  return (
    <footer className="lr-footer">
      <div className="lr-footer-inner">
        <p className="lr-footer-brand">
          {c.brand.productShort} · {c.brand.productLine}
        </p>
        <nav className="lr-footer-links" aria-label="Logos research footer">
          <a href="/logos-research/ask">Q&A</a>
          <a href="/logos-research/studio">Graph Studio</a>
          <a href="/logos-research/docs">Docs</a>
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
