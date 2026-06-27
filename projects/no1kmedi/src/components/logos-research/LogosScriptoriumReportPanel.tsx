"use client";

import { buildScriptoriumReportSections } from "@/lib/logosResearchStudioDisplayV1";

import type { StoryboardResult } from "@/components/logos-research/LogosResearchStoryboardPanel";

type Props = {
  result: StoryboardResult;
};

export function LogosScriptoriumReportPanel({ result }: Props) {
  const sections = buildScriptoriumReportSections({
    answer: result.answer,
    path: result.path,
    insight_card: result.insight_card,
  });

  return (
    <article className="lr-scriptorium-report" aria-labelledby="lr-studio-storyboard-title">
      {sections.map((section) => (
        <section key={section.id} className="lr-scriptorium-report-section">
          <h4 className="lr-scriptorium-report-heading">{section.title}</h4>
          {section.paragraphs.map((paragraph) => (
            <p key={paragraph.slice(0, 48)} className="lr-scriptorium-report-paragraph">
              {paragraph}
            </p>
          ))}
          {section.bullets.length ? (
            <ul className="lr-scriptorium-report-list">
              {section.bullets.map((bullet) => (
                <li key={bullet.slice(0, 48)}>{bullet}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ))}
    </article>
  );
}
