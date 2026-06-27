import {
  DocsPageHeader,
  LogosResearchDocsShell,
} from "@/components/logos-research/LogosResearchDocsShell";
import { logosResearchDocsCopy } from "@/content/logosResearchDocsCopy";

export const metadata = {
  title: "FAQ",
  description: "Citation integrity, compliance, and send_gate HOLD.",
};

export default function LogosResearchFaqPage() {
  const page = logosResearchDocsCopy.faq;

  return (
    <LogosResearchDocsShell activeId="faq">
      <DocsPageHeader eyebrow={page.eyebrow} title={page.title} />

      <div className="lr-docs-faq">
        {page.items.map((item) => (
          <details key={item.q} className="lr-docs-faq-item">
            <summary>{item.q}</summary>
            <p>{item.a}</p>
          </details>
        ))}
      </div>
    </LogosResearchDocsShell>
  );
}
