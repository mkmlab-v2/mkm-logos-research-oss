import {
  DocsPageHeader,
  LogosResearchDocsShell,
} from "@/components/logos-research/LogosResearchDocsShell";
import { logosResearchDocsCopy } from "@/content/logosResearchDocsCopy";

export const metadata = {
  title: "Glossary",
  description: "S-L-K-M, Matching Layer, citation lock, and public terminology fences.",
};

export default function LogosResearchGlossaryPage() {
  const page = logosResearchDocsCopy.glossary;

  return (
    <LogosResearchDocsShell activeId="glossary">
      <DocsPageHeader eyebrow={page.eyebrow} title={page.title} lead={page.intro} />

      <dl className="lr-docs-glossary">
        {page.terms.map((entry) => (
          <div key={entry.term} className="lr-docs-glossary-entry">
            <dt>
              {entry.term}
              <span className="lr-docs-glossary-tier">{entry.tier}</span>
            </dt>
            <dd>
              <p>{entry.definition}</p>
              <p className="lr-docs-glossary-not">
                <strong>Not:</strong> {entry.not}
              </p>
            </dd>
          </div>
        ))}
      </dl>

      <section className="lr-docs-section">
        <h2>Forbidden in public ads</h2>
        <ul className="lr-docs-list lr-docs-list--warn">
          {page.forbidden_in_public_ads.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </LogosResearchDocsShell>
  );
}
