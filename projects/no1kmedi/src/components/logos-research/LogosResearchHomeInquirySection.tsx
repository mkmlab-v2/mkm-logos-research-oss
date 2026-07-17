import { logosResearchCopy } from "@/content/logosResearchCopy";

type InquiryHomeCopy = {
  title?: string;
  lead?: string;
  sample_questions?: string[];
};

function sampleHref(q: string): string {
  return `/logos-research/ask?q=${encodeURIComponent(q)}`;
}

/** Sample-question primary path — no duplicate hero CTA. */
export function LogosResearchHomeInquirySection() {
  const inquiry: InquiryHomeCopy | null =
    "inquiry_home" in logosResearchCopy && logosResearchCopy.inquiry_home
      ? (logosResearchCopy.inquiry_home as InquiryHomeCopy)
      : null;
  const samples = inquiry?.sample_questions ?? [];

  return (
    <section id="inquiry" className="lr-section lr-section--alt" aria-labelledby="lr-inquiry-title">
      <h2 id="lr-inquiry-title">{inquiry?.title ?? "샘플 질문으로 시작"}</h2>
      <p className="lr-section-lead">
        {inquiry?.lead ?? "아래 질문을 고르면 베타 Q&A가 바로 열립니다."}
      </p>
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
      <p className="lr-inquiry-docs-hint">
        <a href="/logos-research/docs/how-it-works">작동 방식 문서</a>
      </p>
    </section>
  );
}
