import type { SiteCopy } from "@/content/siteCopy";

type HomepageAppEntryProps = {
  copy: SiteCopy["app_entry"];
};

/** Marketing home → real app surfaces (/consumer, /clinician). Not the chat UI itself. */
export function HomepageAppEntry({ copy }: HomepageAppEntryProps) {
  const cards = [
    { ...copy.consumer, variant: "primary" as const },
    { ...copy.clinician, variant: "ghost" as const },
  ];

  return (
    <section id="app-entry" className="app-entry" aria-labelledby="app-entry-title">
      <h2 id="app-entry-title">{copy.title}</h2>
      <p className="section-lead">{copy.lead}</p>
      <div className="app-entry-grid">
        {cards.map((card) => (
          <article key={card.href} className="card card-lift app-entry-card">
            <h3>{card.title}</h3>
            <p>{card.body}</p>
            <a className={`btn ${card.variant === "primary" ? "btn-primary" : "btn-ghost"}`} href={card.href}>
              {card.cta}
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}
