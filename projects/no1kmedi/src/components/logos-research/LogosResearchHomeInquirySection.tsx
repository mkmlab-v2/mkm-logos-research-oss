import { logosResearchCopy } from "@/content/logosResearchCopy";

type InquiryHomeCopy = {
  title?: string;
  lead?: string;
  cta?: string;
  sample_questions?: string[];
};

function sampleHref(q: string): string {
  return `/logos-research/ask?q=${encodeURIComponent(q)}`;
}

export function LogosResearchHomeInquirySection() {
  const inquiry: InquiryHomeCopy | null =
    "inquiry_home" in logosResearchCopy && logosResearchCopy.inquiry_home
      ? (logosResearchCopy.inquiry_home as InquiryHomeCopy)
      : null;
  const samples = inquiry?.sample_questions ?? [];

  return (
    <section id="inquiry" className="lr-section lr-section--alt" aria-labelledby="lr-inquiry-title">
      <h2 id="lr-inquiry-title">{inquiry?.title ?? "바로 질문하기"}</h2>
      <p className="lr-section-lead">{inquiry?.lead ?? "텍스트 Q&A — citation lock · S1–S5 리포트."}</p>
      <div className="lr-hero-cta">
        <a className="lr-btn lr-btn-primary" href="/logos-research/ask">
          {inquiry?.cta ?? "Q&A 시작"}
        </a>
        <a className="lr-btn lr-btn-ghost" href="/logos-research/docs/how-it-works">
          작동 방식
        </a>
      </div>
      {samples.length ? (
        <ul className="lr-inquiry-samples">
          {samples.map((q: string) => (
            <li key={q}>
              <a href={sampleHref(q)} className="lr-inquiry-sample-link">
                {q}
              </a>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
