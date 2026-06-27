import {
  DocsPageHeader,
  LogosResearchDocsShell,
} from "@/components/logos-research/LogosResearchDocsShell";
import { logosResearchDocsCopy } from "@/content/logosResearchDocsCopy";

export const metadata = {
  title: "How it works",
  description: "Graph Studio citation lock flow and 30s Job preset demo spine.",
};

export default function LogosResearchHowItWorksPage() {
  const page = logosResearchDocsCopy.how_it_works;

  return (
    <LogosResearchDocsShell activeId="how-it-works">
      <DocsPageHeader eyebrow={page.eyebrow} title={page.title} />
      {page.sections.map((section) => (
        <section key={section.heading} className="lr-docs-section">
          <h2>{section.heading}</h2>
          {"paragraphs" in section && section.paragraphs
            ? section.paragraphs.map((p) => <p key={p.slice(0, 24)}>{p}</p>)
            : null}
          {"steps" in section && section.steps ? (
            <ol className="lr-docs-steps">
              {section.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          ) : null}
          {"demo_cta_label" in section && section.demo_cta_label ? (
            <p className="lr-docs-cta">
              <a className="lr-btn lr-btn-primary" href={logosResearchDocsCopy.demo_url} rel="noopener noreferrer">
                {section.demo_cta_label}
              </a>
            </p>
          ) : null}
        </section>
      ))}
    </LogosResearchDocsShell>
  );
}
