import { logosResearchCopy } from "@/content/logosResearchCopy";

type StoryCopy = {
  title?: string;
  problem_title?: string;
  problem_body?: string;
  solution_title?: string;
  solution_body?: string;
};

/** Scannable Problem → Solution block (Bible research language only). */
export function LogosResearchStorySection() {
  const story =
    "story" in logosResearchCopy && logosResearchCopy.story
      ? (logosResearchCopy.story as StoryCopy)
      : null;
  if (!story) return null;

  return (
    <section
      id="story"
      className="lr-section lr-story"
      aria-labelledby="lr-story-title"
      data-logos-story="1"
    >
      <h2 id="lr-story-title">{story.title ?? "왜 LOGOS인가"}</h2>
      <div className="lr-story-grid">
        <article className="lr-story-card lr-story-card--problem">
          <h3>{story.problem_title ?? "일반 챗의 한계"}</h3>
          <p className="lr-prose">{story.problem_body}</p>
        </article>
        <article className="lr-story-card lr-story-card--solution">
          <h3>{story.solution_title ?? "LOGOS 연구 Ask"}</h3>
          <p className="lr-prose">{story.solution_body}</p>
        </article>
      </div>
    </section>
  );
}
