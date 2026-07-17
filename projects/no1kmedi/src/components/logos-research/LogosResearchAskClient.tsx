"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import type { LogosJemaAiResearchHandoffV1 } from "@/lib/logosJemaAiResearchHandoffV1";
import {
  namespaceIntakeHeaders,
  resolveAskSurfaceContext,
} from "@/lib/surfaceContextNamespaceV1";

import type { LogosInquiryReportV1 } from "@/lib/logosInquiryReportV1";
import {
  commanderSummaryLines,
  commanderSummaryText,
  buildPublicCitationLockModel,
  formatIntentCompressChipKo,
  formatLogosAskError,
  formatPublicNarrativeParagraphs,
  isDevMetadataExpandedDefault,
  isPlaceholderAssistantTurn,
  parseReadingPackSections,
  parseS4PublicSections,
  PUBLIC_INQUIRY_DISCLAIMER_KO,
  researchAuxInsightLines,
  shouldShowPublicSchoolCards,
  snapshotExecutiveText,
  splitS4PublicBody,
  type PublicSchoolGroupV1,
} from "@/lib/logosInquiryAskDisplayV1";
import { consumeLogosInquirySse } from "@/lib/logosInquiryStreamClientV1";
import { isLogosInquiryPaymentEnabled } from "@/lib/logosInquiryBetaV1";
import { startLogosProCheckout } from "@/lib/logosInquiryPayappClientV1";
import { LogosResearchAskQuotaBar } from "@/components/logos-research/LogosResearchAskQuotaBar";
import { LogosResearchAskOnboarding } from "@/components/logos-research/LogosResearchAskOnboarding";
import { LogosResearchAskPostFeedbackStrip } from "@/components/logos-research/LogosResearchAskPostFeedbackStrip";
import { LogosResearchAskCitationLockStrip } from "@/components/logos-research/LogosResearchAskCitationLockStrip";
import { LogosResearchAskGraphPanel } from "@/components/logos-research/LogosResearchAskGraphPanel";
import { LogosAskThemeFourbinDisplaySidecar } from "@/components/logos-research/LogosAskThemeFourbinDisplaySidecar";
import { LogosAskEmptyResearchMapV1 } from "@/components/logos-research/LogosAskEmptyResearchMapV1";
import {
  braidRefsEqual,
  nextBraidFocus,
  splitEssayByKnownRefs,
} from "@/lib/logosAskTextGraphBraidV1";
import type { StreamSnapshot } from "@/lib/logosInquiryStreamV1";
import type { LogosTextMvpReportV1 } from "@/lib/logosResearchTextMvpV1";
import { detectCategoryPremiseHint } from "@/lib/logosInquiryCategoryPremiseHintV1";
import { compressIntentForSchoolRouting } from "@/lib/logosSchoolPanelTopicLockV1";

type OutputFormat = "text_mvp_report_v1" | "inquiry_report_v1";

type StreamPhase = "idle" | "snapshot" | "s4" | "done";

/** Keep in sync with live Destiny until next ship; killer-viz stamp is separate. */
const ASK_UI_REV = "20260717a";
/** P2 calm + theme_fourbin always-on mainline + path tab separation (no gematria merge). */
const ASK_KILLER_VIZ_REV = "20260716b";
type AskPathPanelTab = "theme_meaning_net" | "graph_address_path";
const ASK_TURNS_STORAGE_KEY = "logos_ask_turns_v1";
const ASK_ONBOARDING_DISMISS_KEY = "lr_ask_onboarding_dismissed_v1";
const ASK_THREADS_STUB_KEY = "logos_ask_threads_stub_v1";

type InsightViewMode = "essay" | "scholar";

type PersistedAskStateV1 = {
  rev: string;
  turns: ChatTurn[];
  lastReport?: LogosInquiryReportV1 | LogosTextMvpReportV1 | null;
};

function loadPersistedAskState(): PersistedAskStateV1 | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(ASK_TURNS_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedAskStateV1;
    if (parsed.rev !== ASK_UI_REV || !Array.isArray(parsed.turns)) return null;
    return parsed;
  } catch {
    return null;
  }
}

function persistAskState(turns: ChatTurn[], lastReport: LogosInquiryReportV1 | LogosTextMvpReportV1 | null) {
  if (typeof window === "undefined") return;
  try {
    const payload: PersistedAskStateV1 = {
      rev: ASK_UI_REV,
      turns: turns.map((turn) => ({
        ...turn,
        streamPhase: turn.report || turn.textMvpReport ? ("done" as const) : turn.streamPhase,
        streamingS4: turn.report || turn.textMvpReport ? undefined : turn.streamingS4,
      })),
      lastReport,
    };
    sessionStorage.setItem(ASK_TURNS_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    /* quota / private mode — ignore */
  }
}

function ReadingPackAccordion({ readingPack }: { readingPack: string }) {
  const sections = parseReadingPackSections(readingPack);
  if (!sections.length) return null;
  const summary =
    sections.length > 1
      ? `성경 연구 읽기 프레임 (${sections.length}개 Pack)`
      : "성경 연구 읽기 프레임";
  return (
    <details className="lr-ask-reading-pack-details">
      <summary>{summary}</summary>
      <div className="lr-ask-reading-pack-body">
        {sections.map((section) => (
          <article key={section.title} className="lr-ask-reading-pack-card">
            <h4>{section.title}</h4>
            {section.excerpt ? <p>{section.excerpt}</p> : null}
          </article>
        ))}
      </div>
    </details>
  );
}

type ChatTurn = {
  role: "user" | "assistant";
  text: string;
  report?: LogosInquiryReportV1;
  textMvpReport?: LogosTextMvpReportV1;
  snapshot?: StreamSnapshot;
  streamingS4?: string;
  streamPhase?: StreamPhase;
  error?: string;
};

type Props = {
  initialQuestion?: string;
  sampleQuestions?: string[];
  placeholder: string;
  runLabel: string;
  runningLabel: string;
  governance: string;
  emptyHint?: string;
  handoffLabel: string;
  handoffUrl: string;
  exportLabel: string;
  outputFormat?: OutputFormat;
  autorun?: boolean;
};

function ExecutiveSummary({ lines }: { lines: string[] }) {
  if (!lines.length) return null;
  return (
    <section className="lr-ask-exec-summary" aria-label="핵심 요약">
      <h3>핵심 요약</h3>
      <ol>
        {lines.map((line) => (
          <li key={line.slice(0, 64)}>{line}</li>
        ))}
      </ol>
    </section>
  );
}

function ResearchAuxInsights({ lines }: { lines: string[] }) {
  if (!lines.length) return null;
  return (
    <section className="lr-ask-aux-insights" aria-label="연구 보조 레이어">
      <p className="lr-ask-aux-label">연구 보조 · 게마트리아·사상</p>
      <ul>
        {lines.map((line) => (
          <li key={line.slice(0, 64)}>{line}</li>
        ))}
      </ul>
    </section>
  );
}

function TextMvpReportSections({ report }: { report: LogosTextMvpReportV1 }) {
  const s = report.sections;
  const summaryLines = commanderSummaryLines(s.summary.body_ko, s.summary.bullets_ko);
  return (
    <div className="lr-ask-report">
      <ExecutiveSummary lines={summaryLines} />
      <details className="lr-ask-details">
        <summary>{s.summary.title_ko} — 전문 보기</summary>
        <section className="lr-ask-report-section">
          <p>{s.summary.body_ko}</p>
          {s.summary.bullets_ko.length ? (
            <ul>
              {s.summary.bullets_ko.map((b) => (
                <li key={b.slice(0, 48)}>{b}</li>
              ))}
            </ul>
          ) : null}
        </section>
      </details>
      <section className="lr-ask-report-section">
        <h3>{s.citations.title_ko}</h3>
        <p className="lr-ask-muted">{s.citations.note_ko}</p>
        {s.citations.verse_refs.length ? <p>{s.citations.verse_refs.join(" · ")}</p> : null}
      </section>
      {s.school_comparison.groups.length ? (
        <details className="lr-ask-details lr-ask-scholar-details">
          <summary>학자 모드 · 학파 비교</summary>
          <section className="lr-ask-report-section">
            <h3>{s.school_comparison.title_ko}</h3>
            <p className="lr-ask-muted">{s.school_comparison.note_ko}</p>
            {s.school_comparison.groups.map((group) => (
              <div key={group.conflict_group_id ?? group.lexicon_base ?? "g"}>
                {(group.schools ?? []).map((school) => (
                  <p key={`${school.school_tier}-${school.interpretation_ko?.slice(0, 24)}`}>
                    <span className="lr-ask-tag">{school.school_tier}</span> {school.interpretation_ko}
                  </p>
                ))}
              </div>
            ))}
          </section>
        </details>
      ) : null}
      <section className="lr-ask-report-section">
        <h3>{s.word_network.title_ko}</h3>
        <p className="lr-ask-muted">{s.word_network.note_ko}</p>
        {s.word_network.path_steps.length ? (
          <p>{s.word_network.path_steps.slice(0, 8).join(" → ")}</p>
        ) : null}
      </section>
      {s.gematria_insight.rows.length ? (
        <section className="lr-ask-report-section">
          <h3>{s.gematria_insight.title_ko}</h3>
          <p className="lr-ask-muted">{s.gematria_insight.note_ko}</p>
        </section>
      ) : null}
      <p className="lr-ask-governance">{report.governance.disclaimer_ko}</p>
    </div>
  );
}

function PublicSchoolComparisonSection({
  groups,
  conflictSource,
}: {
  groups: PublicSchoolGroupV1[];
  conflictSource?: "live" | "fallback" | "none";
}) {
  if (!groups.length) return null;
  return (
    <section
      className="lr-ask-report-section lr-ask-report-section--schools lr-ask-school-cards--public"
      aria-label="학파별 해석 비교"
      data-lr-ask-school-cards="1"
      data-lr-ask-school-source={conflictSource ?? "none"}
    >
      <h3>학파별 해석 비교</h3>
      <p className="lr-ask-muted">해석 관점을 나란히 둡니다. 단일 결론·실행 지시가 아닙니다.</p>
      {groups.map((group) => {
        const schools = group.schools ?? [];
        if (!schools.length) return null;
        return (
          <div
            key={group.conflict_group_id ?? group.lexicon_base ?? schools[0]?.school_tier}
            className="lr-ask-school-group"
          >
            {schools.map((school) => (
              <article
                key={`${school.school_tier}-${school.interpretation_ko?.slice(0, 32)}`}
                className="lr-ask-school-row lr-ask-school-card"
              >
                <p>
                  <span className="lr-ask-tag">{school.school_tier ?? "school"}</span>{" "}
                  {school.interpretation_ko}
                </p>
                {school.verse_refs?.length ? (
                  <p className="lr-ask-muted">{school.verse_refs.join(" · ")}</p>
                ) : null}
                {school.traditions?.length ? (
                  <p className="lr-ask-muted">{school.traditions.join(" · ")}</p>
                ) : null}
              </article>
            ))}
          </div>
        );
      })}
    </section>
  );
}

function S4EssayInsight({
  body,
  streaming,
  displayQuery = "",
  knownRefs = [],
  braidFocusRef = null,
  onBraidFocusRef,
}: {
  body: string;
  streaming?: boolean;
  displayQuery?: string;
  knownRefs?: string[];
  braidFocusRef?: string | null;
  onBraidFocusRef?: (ref: string) => void;
}) {
  const paragraphs = formatPublicNarrativeParagraphs(body, displayQuery);
  if (!paragraphs.length) {
    return <p className="lr-ask-muted">통찰 생성 중…</p>;
  }
  return (
    <div
      className="lr-ask-s4-essay"
      aria-label="통찰 본문"
      data-lr-ask-braid-essay={onBraidFocusRef ? "1" : undefined}
      data-lr-ask-braid-focus={braidFocusRef || undefined}
    >
      {paragraphs.map((para) => {
        const tokens = onBraidFocusRef
          ? splitEssayByKnownRefs(para, knownRefs)
          : ([{ type: "text" as const, value: para }] as const);
        return (
          <p key={para.slice(0, 48)} className="lr-ask-narrative-p">
            {tokens.map((tok, i) => {
              if (tok.type === "text") {
                return <span key={`t-${i}`}>{tok.value}</span>;
              }
              const active = Boolean(
                braidFocusRef && braidRefsEqual(braidFocusRef, tok.canonical),
              );
              return (
                <button
                  key={`r-${i}-${tok.canonical}`}
                  type="button"
                  className={`lr-ask-braid-ref${active ? " lr-ask-braid-ref--active" : ""}`}
                  data-lr-ask-braid-ref={tok.canonical}
                  data-lr-ask-braid-active={active ? "1" : "0"}
                  aria-pressed={active}
                  title={`${tok.canonical} · 경로 지도에서 강조`}
                  onClick={() => onBraidFocusRef?.(tok.canonical)}
                >
                  {tok.value}
                </button>
              );
            })}
          </p>
        );
      })}
      {streaming ? <span className="lr-ask-stream-cursor" aria-hidden="true" /> : null}
    </div>
  );
}

function S4PublicInsightSections({
  body,
  streaming,
  displayQuery = "",
}: {
  body: string;
  streaming?: boolean;
  displayQuery?: string;
}) {
  const sections = parseS4PublicSections(body, displayQuery);
  const [openSet, setOpenSet] = useState<Set<number>>(() => new Set([0]));

  useEffect(() => {
    const len = sections.length;
    if (!len) return;
    setOpenSet((prev) => {
      const next = new Set(prev);
      if (streaming) {
        next.add(len - 1);
      }
      for (const idx of next) {
        if (idx >= len) next.delete(idx);
      }
      if (!next.size) next.add(0);
      return next;
    });
  }, [sections.length, streaming, body]);

  const toggleSection = useCallback((idx: number) => {
    setOpenSet((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }, []);

  if (!sections.length) {
    return <p className="lr-ask-muted">통찰 생성 중…</p>;
  }

  // D-GEM-ESSAY-2: gematria meaning path — hide ops-y 「N개 관점·탭」kicker for clean default.
  const hideOpsKicker =
    body.includes("수치 확정 아님 · 의미 논쟁 참고") || /의미\s*논쟁/.test(body);

  return (
    <div
      className="lr-ask-s4-sections"
      data-lr-ask-s4-accordion="1"
      aria-label={`통찰 ${sections.length}개 섹션`}
    >
      {hideOpsKicker ? null : (
        <p className="lr-ask-s4-sections-kicker">
          {sections.length}개 관점 · 탭을 열어 S4 통찰을 확인하세요
        </p>
      )}
      {sections.map((section, idx) => {
        const isOpen = openSet.has(idx);
        return (
          <details
            key={`${section.title}-${idx}`}
            className={`lr-ask-s4-section${isOpen ? " lr-ask-s4-section--open" : ""}${streaming && idx === sections.length - 1 ? " lr-ask-s4-section--streaming" : ""}`}
            data-lr-ask-s4-section={idx + 1}
            open={isOpen}
          >
            <summary
              className="lr-ask-s4-section-title"
              onClick={(event) => {
                event.preventDefault();
                toggleSection(idx);
              }}
            >
              <span className="lr-ask-s4-section-title-text">
                <span className="lr-ask-s4-section-index">{idx + 1}</span>
                {section.title}
              </span>
              <span className="lr-ask-s4-section-chevron" aria-hidden="true" />
            </summary>
            <div className="lr-ask-s4-section-panel">
              {section.body.split(/\n\n+/).map((para) => (
                <p key={para.slice(0, 48)} className="lr-ask-s4-section-body">
                  {para}
                </p>
              ))}
            </div>
          </details>
        );
      })}
      {streaming ? <span className="lr-ask-stream-cursor" aria-hidden="true" /> : null}
    </div>
  );
}

function IntentCompressChip({ line }: { line: string | null }) {
  if (!line) return null;
  return (
    <p className="lr-ask-intent-chip" data-lr-ask-intent-chip="1" aria-label="질문 의도">
      <span className="lr-ask-intent-chip-label">질문 의도</span>
      <span className="lr-ask-intent-chip-text">{line}</span>
    </p>
  );
}

/** Right heart pin stack — Citation → G0–G3 → weak banner → path (wireframe pin_order). */
function AskHeartPinStack({
  report,
  snapshot,
  streamingS4,
  streamPhase = "idle",
  inquiryQuery = "",
  scholarMode = false,
  braidFocusRef,
  onBraidFocusRef,
}: {
  report?: LogosInquiryReportV1;
  snapshot?: StreamSnapshot;
  streamingS4?: string;
  streamPhase?: StreamPhase;
  inquiryQuery?: string;
  scholarMode?: boolean;
  braidFocusRef: string | null;
  onBraidFocusRef: (ref: string) => void;
}) {
  const s1 = report?.sections?.S1 ?? snapshot?.S1;
  const s4Body = report?.sections?.S4.body_ko ?? streamingS4 ?? "";
  const gov = report?.governance ?? snapshot?.governance;
  const citationModel = buildPublicCitationLockModel(report, snapshot);
  const graphVerseRefs = s1?.verse_refs ?? [];
  const graphAnchors = s1?.citation_lock_anchors ?? [];
  const askQuery = report?.query ?? inquiryQuery;
  const [pathTab, setPathTab] = useState<AskPathPanelTab>("theme_meaning_net");

  if (!s1 && !s4Body && !citationModel && !gov) return null;

  const gradeId = gov?.control_grade?.id?.toLowerCase() ?? "";
  const grainClass =
    gradeId === "g3"
      ? " lr-ask-heart-stack--grain-g3"
      : gradeId === "g2"
        ? " lr-ask-heart-stack--grain-g2"
        : gradeId === "g0"
          ? " lr-ask-heart-stack--grain-g0"
          : "";

  return (
    <div
      className={`lr-ask-heart-stack${grainClass}${scholarMode ? " lr-ask-heart-stack--scholar" : ""}`}
      data-lr-ask-heart-stack="1"
      data-lr-ask-pin-order="citation_list,control_grade_g0g3,weak_citation_banner,path_panel"
    >
      <div className="lr-ask-heart-sticky-head" data-lr-ask-sticky-head="1">
        <div className="lr-ask-heart-pin lr-ask-heart-pin--citation" data-lr-ask-pin="citation_list">
          {citationModel ? (
            <LogosResearchAskCitationLockStrip
              model={citationModel}
              variant={scholarMode ? "scholar" : "viewport"}
              braidFocusRef={braidFocusRef}
              onBraidFocusRef={onBraidFocusRef}
            />
          ) : (
            <p className="lr-ask-muted lr-ask-heart-empty">근거 구절이 아직 없습니다.</p>
          )}
        </div>

        {gov?.control_grade ? (
          <aside
            className={`lr-ask-control-grade-badge lr-ask-control-grade-badge--${gov.control_grade.id.toLowerCase()} lr-ask-heart-pin lr-ask-heart-pin--grade`}
            role="status"
            data-lr-ask-pin="control_grade_g0g3"
            data-lr-ask-control-grade={gov.control_grade.id}
            data-lr-ask-control-intensity={gov.control_grade.intensity}
            data-lr-ask-control-score-kind={gov.control_grade.score_kind}
            aria-label={`통제 등급 ${gov.control_grade.id}`}
          >
            <span className="lr-ask-control-grade-id">{gov.control_grade.id}</span>
            <span className="lr-ask-control-grade-label">{gov.control_grade.label_ko}</span>
          </aside>
        ) : null}

        {gov?.honest_control_banner_ko ? (
          <aside
            className="lr-ask-honest-control-banner lr-ask-heart-pin lr-ask-heart-pin--weak"
            role="status"
            data-lr-ask-pin="weak_citation_banner"
            data-lr-ask-honest-control="1"
            data-lr-ask-citation-strength={gov.citation_strength ?? "soft"}
          >
            <p className="lr-ask-honest-control-banner-text">{gov.honest_control_banner_ko}</p>
          </aside>
        ) : null}
      </div>

      <div className="lr-ask-heart-pin lr-ask-heart-pin--path" data-lr-ask-pin="path_panel">
        {/* W6: theme meaning-net vs graph/address path — separate tabs; no gematria merge */}
        <div
          className="lr-ask-path-tab-shell"
          data-lr-ask-path-tabs="1"
          data-lr-ask-path-tab-active={pathTab}
          data-address-book-merge="false"
        >
          <div className="lr-ask-path-tablist" role="tablist" aria-label="경로 패널 구분">
            <button
              type="button"
              role="tab"
              id="lr-ask-tab-theme-meaning-net"
              className={`lr-ask-path-tab${pathTab === "theme_meaning_net" ? " lr-ask-path-tab--active" : ""}`}
              aria-selected={pathTab === "theme_meaning_net"}
              data-lr-ask-path-tab="theme_meaning_net"
              onClick={() => setPathTab("theme_meaning_net")}
            >
              테마 4칸
            </button>
            <button
              type="button"
              role="tab"
              id="lr-ask-tab-graph-address-path"
              className={`lr-ask-path-tab${pathTab === "graph_address_path" ? " lr-ask-path-tab--active" : ""}`}
              aria-selected={pathTab === "graph_address_path"}
              data-lr-ask-path-tab="graph_address_path"
              onClick={() => setPathTab("graph_address_path")}
            >
              연결망
            </button>
          </div>

          <div
            role="tabpanel"
            id="lr-ask-panel-theme-meaning-net"
            aria-labelledby="lr-ask-tab-theme-meaning-net"
            hidden={pathTab !== "theme_meaning_net"}
            className="lr-ask-path-tabpanel lr-ask-path-tabpanel--theme"
            data-lr-ask-path-panel="theme_meaning_net"
            data-gematria-merge="false"
          >
            <LogosAskThemeFourbinDisplaySidecar
              verseRefs={graphVerseRefs}
              query={askQuery}
              answerText={s4Body}
              alwaysOnMainline
            />
          </div>

          <div
            role="tabpanel"
            id="lr-ask-panel-graph-address-path"
            aria-labelledby="lr-ask-tab-graph-address-path"
            hidden={pathTab !== "graph_address_path"}
            className="lr-ask-path-tabpanel lr-ask-path-tabpanel--graph"
            data-lr-ask-path-panel="graph_address_path"
          >
            {graphVerseRefs.length ? (
              <div className="lr-ask-graph-panel-wrap lr-ask-graph-panel-wrap--heart">
                <LogosResearchAskGraphPanel
                  query={askQuery}
                  verseRefs={graphVerseRefs}
                  citationLockAnchors={graphAnchors}
                  presetId={report?.preset_id}
                  streamPhase={streamPhase}
                  height={scholarMode ? 360 : 280}
                  braidFocusRef={braidFocusRef}
                  onBraidFocusRef={onBraidFocusRef}
                />
              </div>
            ) : (
              <LogosAskEmptyResearchMapV1 />
            )}
          </div>
        </div>
      </div>

      <p className="lr-ask-heart-rev" aria-hidden="true">
        UI {ASK_UI_REV} · killer {ASK_KILLER_VIZ_REV}
      </p>
    </div>
  );
}

function AskThreadRailStub({
  sessionTitle,
  onNewChat,
}: {
  sessionTitle: string;
  onNewChat: () => void;
}) {
  return (
    <aside className="lr-ask-thread-rail" data-lr-ask-thread-rail="1" aria-label="대화 목록 (로컬)">
      <div className="lr-ask-thread-rail-head">
        <p className="lr-ask-thread-rail-eyebrow">이 세션</p>
        <button type="button" className="lr-btn lr-btn-ghost lr-ask-thread-new" onClick={onNewChat}>
          새 대화
        </button>
      </div>
      <p className="lr-ask-thread-rail-hint">검색·스레드 동기화는 아직 없음</p>
      <ul className="lr-ask-thread-list" role="list">
        <li>
          <button type="button" className="lr-ask-thread-item lr-ask-thread-item--active" aria-current="true">
            <span className="lr-ask-thread-item-title">{sessionTitle}</span>
            <span className="lr-ask-thread-item-meta">로컬</span>
          </button>
        </li>
      </ul>
      <p className="lr-ask-thread-rail-note">로컬만 · 초대 없음</p>
    </aside>
  );
}

function ReportSections({
  report,
  snapshot,
  streamingS4,
  streamPhase = "idle",
  inquiryQuery = "",
  insightView,
  onInsightViewChange,
  braidFocusRef,
  onBraidFocusRef,
}: {
  report?: LogosInquiryReportV1;
  snapshot?: StreamSnapshot;
  streamingS4?: string;
  streamPhase?: StreamPhase;
  inquiryQuery?: string;
  insightView: InsightViewMode;
  onInsightViewChange: (mode: InsightViewMode) => void;
  braidFocusRef: string | null;
  onBraidFocusRef: (ref: string) => void;
}) {
  const s = report?.sections;
  const s1 = s?.S1 ?? snapshot?.S1;
  const s2 = s?.S2 ?? snapshot?.S2;
  const s3 = s?.S3 ?? snapshot?.S3;
  const s4Body = s?.S4.body_ko ?? streamingS4 ?? "";
  const s4Bullets = s?.S4.bullets_ko ?? [];
  const s5 = s?.S5 ?? snapshot?.S5;
  const gov = report?.governance ?? snapshot?.governance;
  const s4Streaming = streamPhase === "s4" && !report;
  const auxLines = researchAuxInsightLines(s2, s3);
  const { readingPack } = splitS4PublicBody(s4Body);
  const scholarMode = insightView === "scholar";

  const citationModel = buildPublicCitationLockModel(report, snapshot);
  const graphVerseRefs = s1?.verse_refs ?? [];
  const graphAnchors = s1?.citation_lock_anchors ?? [];

  const braidKnownRefs = useMemo(() => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const r of [...graphVerseRefs, ...graphAnchors, ...(citationModel?.verseRefs ?? [])]) {
      const t = String(r || "").trim();
      if (!t || seen.has(t)) continue;
      seen.add(t);
      out.push(t);
    }
    return out;
  }, [citationModel?.verseRefs, graphAnchors, graphVerseRefs]);

  if (!s1 && !s4Body) return null;

  const devMetaDefaultOpen = isDevMetadataExpandedDefault();

  const schoolGroups = (s3?.groups ?? []) as PublicSchoolGroupV1[];
  const schoolConflictSource = (s3 as { conflict_source?: "live" | "fallback" | "none" } | undefined)
    ?.conflict_source;
  const showSchoolCards =
    scholarMode && shouldShowPublicSchoolCards(inquiryQuery || report?.query || "", schoolGroups);
  const premiseHint = detectCategoryPremiseHint(inquiryQuery || report?.query || "");
  const intentChip = formatIntentCompressChipKo(
    (s3 as { intent_compress?: Parameters<typeof formatIntentCompressChipKo>[0] } | undefined)
      ?.intent_compress ?? compressIntentForSchoolRouting(inquiryQuery || report?.query || ""),
  );

  return (
    <div
      className={`lr-ask-report${scholarMode ? " lr-ask-report--scholar" : " lr-ask-report--clean"}`}
      data-lr-ask-ux={scholarMode ? "scholar" : "clean"}
      data-lr-ask-braid="1"
      data-lr-ask-braid-focus={braidFocusRef || undefined}
      data-lr-ask-canvas-report="1"
    >
      <div className="lr-ask-report-primary">
        {premiseHint && scholarMode ? (
          <aside
            className="lr-ask-premise-hint"
            role="note"
            data-lr-ask-premise-hint={premiseHint.code}
            data-lr-ask-premise-gating={premiseHint.gating_status}
          >
            <p className="lr-ask-premise-hint-title">{premiseHint.title_ko}</p>
            <p className="lr-ask-premise-hint-body">{premiseHint.hint_ko}</p>
            <p className="lr-ask-premise-hint-reframe">{premiseHint.suggested_reframe_ko}</p>
          </aside>
        ) : null}
        {scholarMode ? <IntentCompressChip line={intentChip} /> : null}
        <section
          className={`lr-ask-report-section lr-ask-report-section--primary${s4Streaming ? " lr-ask-s4-streaming" : ""}`}
          aria-live={s4Streaming ? "polite" : undefined}
        >
          <div className="lr-ask-insight-head">
            <h3>통찰</h3>
            {s4Body ? (
              <div className="lr-ask-insight-view-toggle" role="group" aria-label="통찰 보기 방식">
                <button
                  type="button"
                  className={`lr-ask-insight-view-btn${insightView === "essay" ? " lr-ask-insight-view-btn--active" : ""}`}
                  aria-pressed={insightView === "essay"}
                  data-lr-ask-view="essay"
                  onClick={() => onInsightViewChange("essay")}
                >
                  기본
                </button>
                <button
                  type="button"
                  className={`lr-ask-insight-view-btn${insightView === "scholar" ? " lr-ask-insight-view-btn--active" : ""}`}
                  aria-pressed={insightView === "scholar"}
                  data-lr-ask-view="scholar"
                  onClick={() => onInsightViewChange("scholar")}
                >
                  학자 모드
                </button>
              </div>
            ) : null}
          </div>
          {s4Body ? (
            scholarMode ? (
              <S4PublicInsightSections
                body={s4Body}
                streaming={s4Streaming}
                displayQuery={inquiryQuery || report?.query || ""}
              />
            ) : (
              <S4EssayInsight
                body={s4Body}
                streaming={s4Streaming}
                displayQuery={inquiryQuery || report?.query || ""}
                knownRefs={braidKnownRefs}
                braidFocusRef={braidFocusRef}
                onBraidFocusRef={onBraidFocusRef}
              />
            )
          ) : (
            <p className="lr-ask-muted">통찰 생성 중…</p>
          )}
        </section>

        {showSchoolCards ? (
          <PublicSchoolComparisonSection groups={schoolGroups} conflictSource={schoolConflictSource} />
        ) : null}

        {scholarMode && readingPack ? (
          <section className="lr-ask-report-section lr-ask-report-section--packs">
            <ReadingPackAccordion readingPack={readingPack} />
          </section>
        ) : null}

        <p className="lr-ask-governance lr-ask-governance--public">{PUBLIC_INQUIRY_DISCLAIMER_KO}</p>
      </div>

      {devMetaDefaultOpen ? (
      <details className="lr-ask-dev-metadata" open={devMetaDefaultOpen}>
        <summary>연구원용 검증 메타데이터 (재현성·해시 핀)</summary>
        <div className="lr-ask-dev-metadata-body">
          <nav className="lr-ask-section-rail" aria-label="5-section inquiry report">
            <span className={`lr-ask-section-pill${s1 ? " lr-ask-section-pill--ready" : ""}`}>S1</span>
            <span className={`lr-ask-section-pill${s2 ? " lr-ask-section-pill--ready" : ""}`}>S2</span>
            <span className={`lr-ask-section-pill${s3 ? " lr-ask-section-pill--ready" : ""}`}>S3</span>
            <span className={`lr-ask-section-pill${s4Body ? " lr-ask-section-pill--ready" : ""}`}>S4</span>
            <span
              className={`lr-ask-section-pill${s5?.signoff_status === "final" ? " lr-ask-section-pill--ready" : s5 ? " lr-ask-section-pill--provisional" : ""}`}
            >
              S5
            </span>
          </nav>
          <ResearchAuxInsights lines={auxLines} />
          {s1 ? (
            <section className="lr-ask-report-section">
              <h3>{s1.title_ko}</h3>
              <p className="lr-ask-muted">{s1.security_note_ko}</p>
              {s1.verse_refs.length ? <p>{s1.verse_refs.join(" · ")}</p> : <p className="lr-ask-muted">—</p>}
            </section>
          ) : null}
      {s2 ? (
        <section className="lr-ask-report-section">
          <h3>{s2.title_ko}</h3>
          <p className="lr-ask-muted">{s2.security_note_ko}</p>
          <p className="lr-ask-muted">
            lemma lines {s2.lemma_edge_line_count ?? "—"} / floor {s2.min_line_count_floor}
          </p>
          {s2.path_token_preview?.length ? (
            <p className="lr-ask-path-preview">
              <span className="lr-ask-tag">lemma·경로</span>{" "}
              {s2.path_token_preview.slice(0, 12).join(" · ")}
            </p>
          ) : null}
        </section>
      ) : null}
      {s3 ? (
        <section className="lr-ask-report-section">
          <h3>{s3.title_ko}</h3>
          <p className="lr-ask-muted">{s3.note_ko}</p>
          {(s3.groups ?? []).map((raw) => {
            const group = raw as {
              conflict_group_id?: string;
              lexicon_base?: string;
              school_count?: number;
              schools?: Array<{
                school_tier?: string;
                interpretation_ko?: string;
                verse_refs?: string[];
                traditions?: string[];
              }>;
            };
            const schools = group.schools ?? [];
            if (!schools.length) return null;
            return (
              <div
                key={group.conflict_group_id ?? group.lexicon_base ?? schools[0]?.school_tier}
                className="lr-ask-school-group"
              >
                {group.lexicon_base ? (
                  <p className="lr-ask-muted">
                    lemma · {group.lexicon_base}
                    {group.school_count ? ` · ${group.school_count} school(s)` : ""}
                  </p>
                ) : null}
                {schools.map((school) => (
                  <div
                    key={`${school.school_tier}-${school.interpretation_ko?.slice(0, 32)}`}
                    className="lr-ask-school-row"
                  >
                    <p>
                      <span className="lr-ask-tag">{school.school_tier ?? "school"}</span>{" "}
                      {school.interpretation_ko}
                    </p>
                    {school.verse_refs?.length ? (
                      <p className="lr-ask-muted">{school.verse_refs.join(" · ")}</p>
                    ) : null}
                    {school.traditions?.length ? (
                      <p className="lr-ask-muted">{school.traditions.join(" · ")}</p>
                    ) : null}
                  </div>
                ))}
              </div>
            );
          })}
        </section>
      ) : null}
      {s5 ? (
        <section className="lr-ask-report-section">
          <h3>{s5.title_ko}</h3>
          <p className="lr-ask-muted">
            {s5.signoff_status === "provisional"
              ? "서명 provisional — S4 완료 대기"
              : `final seal · exit ${s5.chain_exit_code} · sha256 ${String(s5.sections_payload_sha256).slice(0, 16)}…`}
          </p>
        </section>
      ) : null}
      {s4Bullets.length ? (
        <section className="lr-ask-report-section">
          <h3>S4 기술 메모</h3>
          <ul>
            {s4Bullets.map((b) => (
              <li key={b.slice(0, 48)}>{b}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {gov ? <p className="lr-ask-governance">{gov.disclaimer_ko}</p> : null}
        </div>
      </details>
      ) : null}
    </div>
  );
}

export function LogosResearchAskClient({
  initialQuestion = "",
  sampleQuestions = [],
  placeholder,
  runLabel,
  runningLabel,
  governance,
  emptyHint,
  handoffLabel,
  handoffUrl,
  exportLabel,
  outputFormat = "inquiry_report_v1",
  autorun = false,
}: Props) {
  const [question, setQuestion] = useState(initialQuestion);
  const restored = useMemo(() => loadPersistedAskState(), []);
  const [turns, setTurns] = useState<ChatTurn[]>(() => restored?.turns ?? []);
  const [running, setRunning] = useState(false);
  const autorunOnceRef = useRef(false);
  const [chatExpanded, setChatExpanded] = useState(() => (restored?.turns?.length ?? 0) > 0);
  const [checkoutEmail, setCheckoutEmail] = useState("");
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [checkoutNote, setCheckoutNote] = useState<string | null>(null);
  const [quotaRefresh, setQuotaRefresh] = useState(0);
  const paymentUiEnabled = isLogosInquiryPaymentEnabled();
  const [lastReport, setLastReport] = useState<LogosInquiryReportV1 | LogosTextMvpReportV1 | null>(
    () => restored?.lastReport ?? null,
  );
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const searchParams = useSearchParams();
  const [handoffDoc, setHandoffDoc] = useState<LogosJemaAiResearchHandoffV1 | null>(null);
  const [onboardingOpen, setOnboardingOpen] = useState(true);
  const [insightView, setInsightView] = useState<InsightViewMode>("essay");
  const [braidFocusRef, setBraidFocusRef] = useState<string | null>(null);
  const [heartDrawerOpen, setHeartDrawerOpen] = useState(false);
  const showDevChrome = isDevMetadataExpandedDefault();

  const onBraidFocusRef = useCallback((ref: string) => {
    setBraidFocusRef((prev) => nextBraidFocus(prev, ref));
    setHeartDrawerOpen(true);
    if (typeof document !== "undefined") {
      window.requestAnimationFrame(() => {
        const chip = document.querySelector(
          `[data-lr-ask-braid-ref="${CSS.escape(ref)}"].lr-ask-citation-lock-ref-chip`,
        );
        chip?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        const panel = document.querySelector("[data-logos-ask-graph='1']");
        panel?.scrollIntoView({ block: "nearest", behavior: "smooth" });
      });
    }
  }, []);

  const startNewChat = useCallback(() => {
    setTurns([]);
    setLastReport(null);
    setBraidFocusRef(null);
    setQuestion("");
    setChatExpanded(false);
    setInsightView("essay");
    try {
      sessionStorage.removeItem(ASK_TURNS_STORAGE_KEY);
      localStorage.setItem(
        ASK_THREADS_STUB_KEY,
        JSON.stringify({ rev: ASK_UI_REV, active_title: "새 대화", updated_at: Date.now() }),
      );
    } catch {
      /* ignore */
    }
  }, []);

  const adjustInputHeight = useCallback(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 168)}px`;
  }, []);

  useEffect(() => {
    try {
      setOnboardingOpen(window.localStorage.getItem(ASK_ONBOARDING_DISMISS_KEY) !== "1");
    } catch {
      setOnboardingOpen(true);
    }
  }, []);

  useEffect(() => {
    adjustInputHeight();
  }, [question, adjustInputHeight]);

  useEffect(() => {
    if (!turns.length && !lastReport) return;
    persistAskState(turns, lastReport);
  }, [turns, lastReport]);

  useEffect(() => {
    let cancelled = false;
    void fetch("/data/logos_jema_ai_research_handoff_v1.json")
      .then((r) => (r.ok ? r.json() : null))
      .then((doc) => {
        if (!cancelled && doc && typeof doc === "object") {
          setHandoffDoc(doc as LogosJemaAiResearchHandoffV1);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const surfaceContext = useMemo(
    () =>
      resolveAskSurfaceContext({
        handoff: handoffDoc,
        searchParams,
      }),
    [handoffDoc, searchParams],
  );

  const submit = useCallback(async (overrideQuestion?: string) => {
    const q = (overrideQuestion ?? question).trim();
    if (!q || running) return;
    setRunning(true);
    setQuestion("");
    let assistantIdx = 0;
    setTurns((prev) => {
      assistantIdx = prev.length + 1;
      return [
        ...prev,
        { role: "user" as const, text: q },
        { role: "assistant" as const, text: "연결 중…", streamingS4: "", streamPhase: "idle" as const },
      ];
    });

    try {
      const useTextMvp = outputFormat === "text_mvp_report_v1";
      const controller = new AbortController();
      const timeoutMs = 180_000;
      const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
      const res = await fetch("/api/logos-research/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...namespaceIntakeHeaders(handoffDoc),
          "X-JEMA-Domain-Surface-Hint": surfaceContext.domain_surface_hint,
        },
        body: JSON.stringify({
          query: q,
          output_format: outputFormat,
          stream_s4: !useTextMvp,
          domain_lane: surfaceContext.domain_lane,
          domain_surface_hint: surfaceContext.domain_surface_hint,
          intent_chip: "reports",
          azure_distill_mode: "auto",
        }),
        signal: controller.signal,
      });
      window.clearTimeout(timeoutId);

      if (!res.ok) {
        const errBody = (await res.json().catch(() => ({}))) as {
          error?: string;
          hint?: string;
          reverse_questions_ko?: string[];
          remaining?: number;
          free_daily_quota?: number;
        };
        const err = formatLogosAskError(
          errBody.error,
          errBody.error === "quota_exceeded"
            ? `오늘 무료 ${errBody.free_daily_quota ?? 8}회를 모두 사용했습니다. UTC 자정 이후 리셋 · GitHub Issues로 피드백 주세요.`
            : errBody.hint,
          errBody.reverse_questions_ko,
        );
        setTurns((prev) => {
          const next = [...prev];
          next[assistantIdx] = { role: "assistant", text: err, error: err };
          return next;
        });
        setQuotaRefresh((n) => n + 1);
        return;
      }

      if (useTextMvp || !res.headers.get("content-type")?.includes("text/event-stream")) {
        const data = (await res.json()) as {
          ok?: boolean;
          report?: LogosInquiryReportV1 | LogosTextMvpReportV1;
          error?: string;
          hint?: string;
          reverse_questions_ko?: string[];
        };
        if (!data.ok || !data.report) {
          const err = formatLogosAskError(
            data.error,
            data.hint,
            data.reverse_questions_ko,
          );
          setTurns((prev) => {
            const next = [...prev];
            next[assistantIdx] = { role: "assistant", text: err, error: err };
            return next;
          });
          return;
        }
        setLastReport(data.report);
        const bodyText = useTextMvp
          ? (data.report as LogosTextMvpReportV1).sections.summary.body_ko
          : (data.report as LogosInquiryReportV1).sections.S4.body_ko;
        const bullets = useTextMvp
          ? (data.report as LogosTextMvpReportV1).sections.summary.bullets_ko
          : (data.report as LogosInquiryReportV1).sections.S4.bullets_ko;
        const summaryText = commanderSummaryText(bodyText, bullets);
        setTurns((prev) => {
          const next = [...prev];
          next[assistantIdx] = useTextMvp
            ? {
                role: "assistant",
                text: summaryText,
                textMvpReport: data.report as LogosTextMvpReportV1,
              }
            : {
                role: "assistant",
                text: summaryText,
                report: data.report as LogosInquiryReportV1,
              };
          return next;
        });
        return;
      }

      let s4Accum = "";
      const clientPaceMs =
        typeof process.env.NEXT_PUBLIC_LOGOS_INQUIRY_STREAM_PACE_MS === "string"
          ? Math.max(0, parseInt(process.env.NEXT_PUBLIC_LOGOS_INQUIRY_STREAM_PACE_MS, 10) || 0)
          : 0;
      await consumeLogosInquirySse(res, {
        paceMs: clientPaceMs,
        onSnapshot: (snap) => {
          const teaser = snapshotExecutiveText(snap as StreamSnapshot);
          setTurns((prev) => {
            const next = [...prev];
            next[assistantIdx] = {
              ...next[assistantIdx],
              snapshot: snap as StreamSnapshot,
              streamPhase: "snapshot",
              text: teaser || "S1–S3 준비 완료 · S4 수신 중…",
            };
            return next;
          });
        },
        onS4Delta: (text) => {
          s4Accum += text;
          const preview = commanderSummaryText(s4Accum);
          setTurns((prev) => {
            const next = [...prev];
            next[assistantIdx] = {
              ...next[assistantIdx],
              streamPhase: "s4",
              streamingS4: s4Accum,
              text: preview || "…",
            };
            return next;
          });
        },
        onS4Done: (body) => {
          s4Accum = body;
          const preview = commanderSummaryText(body);
          setTurns((prev) => {
            const next = [...prev];
            next[assistantIdx] = {
              ...next[assistantIdx],
              streamPhase: "s4",
              streamingS4: body,
              text: preview || "…",
            };
            return next;
          });
        },
        onDone: (report) => {
          const r = report as LogosInquiryReportV1;
          setLastReport(r);
          const summaryText = commanderSummaryText(r.sections.S4.body_ko, r.sections.S4.bullets_ko);
          setTurns((prev) => {
            const next = [...prev];
            next[assistantIdx] = {
              role: "assistant",
              text: summaryText,
              report: r,
              streamPhase: "done",
              streamingS4: undefined,
            };
            return next;
          });
        },
        onError: (message) => {
          const err = formatLogosAskError(message, message);
          setTurns((prev) => {
            const next = [...prev];
            next[assistantIdx] = { role: "assistant", text: err, error: err };
            return next;
          });
        },
      });
    } catch (error: unknown) {
      if (error instanceof Error && error.name === "AbortError") {
        const err =
          "응답 시간이 초과되었습니다(3분). 잠시 후 다시 시도하거나 질문을 더 구체화해 주세요.";
        setTurns((prev) => {
          const next = [...prev];
          next[assistantIdx] = { role: "assistant", text: err, error: err };
          return next;
        });
      } else {
        const raw = error instanceof Error ? error.message : "query_failed";
        const err = formatLogosAskError(raw);
        setTurns((prev) => {
          const next = [...prev];
          const painted = next[assistantIdx]?.text || "";
          // Keep onError Korean paint if already clean; otherwise format.
          if (!painted || /preset_missing|preset_not_matched|연결 중/i.test(painted)) {
            next[assistantIdx] = { role: "assistant", text: err, error: err };
          } else if (/preset_missing|preset_not_matched/i.test(painted)) {
            next[assistantIdx] = { role: "assistant", text: err, error: err };
          }
          return next;
        });
      }
    } finally {
      setRunning(false);
      setQuotaRefresh((n) => n + 1);
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [question, running, outputFormat, surfaceContext, handoffDoc]);

  useEffect(() => {
    if (!autorun || autorunOnceRef.current || running || turns.length > 0) return;
    const typed = question.trim();
    const fallback = sampleQuestions.map((s) => s.trim()).find((s) => s.length >= 12) ?? "";
    const pick = typed.length >= 12 ? typed : fallback;
    if (pick.length < 12) return;
    if (pick !== typed) setQuestion(pick);
    autorunOnceRef.current = true;
    void submit(pick);
  }, [autorun, question, running, turns.length, submit, sampleQuestions]);

  const pickSampleQuestion = useCallback(
    (sample: string) => {
      void submit(sample);
    },
    [submit],
  );

  const exportJson = useCallback(() => {
    if (!lastReport) return;
    const schema = "schema" in lastReport ? lastReport.schema : "logos_inquiry_report_v1";
    const blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${schema}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [lastReport]);

  const startProCheckout = useCallback(async () => {
    const email = checkoutEmail.trim();
    if (!email || checkoutBusy) return;
    setCheckoutBusy(true);
    setCheckoutNote(null);
    try {
      const result = await startLogosProCheckout(email);
      if (!result.success) {
        setCheckoutNote(
          result.g12_human_inject
            ? "Pro 결제는 서버 키(G12) 주입 후 가능합니다."
            : result.error || "checkout_failed",
        );
        return;
      }
      setCheckoutNote(result.note_ko || "주문이 생성되었습니다.");
      if (result.redirect_url && !result.dry_run_keys) {
        window.location.href = result.redirect_url;
      }
    } catch (error: unknown) {
      setCheckoutNote(error instanceof Error ? error.message : "checkout_failed");
    } finally {
      setCheckoutBusy(false);
    }
  }, [checkoutEmail, checkoutBusy]);

  const hasInquiryReport = turns.some(
    (turn) =>
      turn.role === "assistant" &&
      !turn.error &&
      (turn.report != null || turn.snapshot != null),
  );

  const heartSource = useMemo(() => {
    for (let i = turns.length - 1; i >= 0; i -= 1) {
      const turn = turns[i];
      if (turn.role !== "assistant" || turn.error) continue;
      if (!turn.report && !turn.snapshot) continue;
      const userQuery = i > 0 && turns[i - 1]?.role === "user" ? turns[i - 1].text : "";
      return { turn, userQuery };
    }
    return null;
  }, [turns]);

  const sessionTitle = useMemo(() => {
    const firstUser = turns.find((t) => t.role === "user");
    if (firstUser?.text?.trim()) {
      const t = firstUser.text.trim();
      return t.length > 36 ? `${t.slice(0, 36)}…` : t;
    }
    return "새 대화";
  }, [turns]);

  return (
    <div
      className={`lr-ask lr-ask--hybrid-shell${chatExpanded ? " lr-ask--report-expanded" : ""}${heartDrawerOpen ? " lr-ask--heart-open" : ""}`}
      data-logos-ask-ui-rev={ASK_UI_REV}
      data-lr-ask-killer-viz={ASK_KILLER_VIZ_REV}
      data-lr-ask-hybrid-shell="1"
    >
      <AskThreadRailStub sessionTitle={sessionTitle} onNewChat={startNewChat} />

      {heartDrawerOpen ? (
        <button
          type="button"
          className="lr-ask-heart-drawer-backdrop"
          aria-label="출처·통제 패널 닫기"
          onClick={() => setHeartDrawerOpen(false)}
        />
      ) : null}

      <div className="lr-ask-canvas" data-lr-ask-canvas="1">
        {showDevChrome ? (
          <p className="lr-ask-ui-rev-badge" aria-hidden="true">
            UI {ASK_UI_REV} · killer {ASK_KILLER_VIZ_REV} · TE hybrid
          </p>
        ) : null}
        {turns.length === 0 ? (
          <div className="lr-ask-first-paint" data-lr-ask-first-paint="1">
            <LogosResearchAskOnboarding
              onPickSample={pickSampleQuestion}
              onDismiss={() => setOnboardingOpen(false)}
            />
            {/* Narrow only: heart is drawer below 840 — show one ghost map in canvas */}
            <div
              className="lr-ask-first-paint-map lr-ask-first-paint-map--narrow"
              data-lr-ask-first-paint-map="narrow"
            >
              <LogosAskEmptyResearchMapV1 />
            </div>
          </div>
        ) : null}
        <div className="lr-ask-chat-toolbar">
          <button
            type="button"
            className="lr-btn lr-btn-ghost lr-ask-heart-drawer-toggle"
            aria-expanded={heartDrawerOpen}
            aria-controls="lr-ask-heart-rail"
            onClick={() => setHeartDrawerOpen((open) => !open)}
          >
            {heartDrawerOpen ? "출처·통제 닫기" : "출처·통제 · 연구 지도"}
          </button>
          {hasInquiryReport ? (
            <button
              type="button"
              className="lr-btn lr-btn-ghost lr-ask-expand-btn"
              aria-pressed={chatExpanded}
              onClick={() => setChatExpanded((open) => !open)}
            >
              {chatExpanded ? "기본 보기" : "리포트 넓게"}
            </button>
          ) : null}
        </div>
        <div
          className={`lr-ask-chat${chatExpanded ? " lr-ask-chat--expanded" : ""}`}
          ref={listRef}
          aria-live="polite"
        >
          {turns.length === 0 ? (
            <div className="lr-ask-empty-block">
              <p className="lr-ask-empty-vp">
                {emptyHint ??
                  "아래에서 바로 질문하거나, 샘플을 고르세요. 첫 답은 인용 탭부터 확인하면 됩니다."}
              </p>
              <p className="lr-ask-empty">{governance}</p>
            </div>
          ) : (
            turns.filter((turn) => !isPlaceholderAssistantTurn(turn)).map((turn, i) => (
              <div
                key={`${turn.role}-${i}-${turn.text.slice(0, 24)}`}
                className={`lr-ask-turn lr-ask-turn--${turn.role}${turn.error ? " lr-ask-turn--error" : ""}${turn.streamPhase && turn.streamPhase !== "done" ? " lr-ask-turn--streaming" : ""}`}
              >
                <span className="lr-ask-role">{turn.role === "user" ? "질문" : "답변"}</span>
                {turn.role === "assistant" &&
                turn.report &&
                (turn.streamPhase === "done" || turn.streamPhase === undefined) ? null : (
                  <div className="lr-ask-bubble lr-ask-bubble--summary">
                    {turn.text || (turn.role === "assistant" ? "…" : turn.text)}
                  </div>
                )}
                {turn.role === "assistant" && turn.textMvpReport ? (
                  <TextMvpReportSections report={turn.textMvpReport} />
                ) : turn.role === "assistant" && (turn.report || turn.snapshot) ? (
                  <ReportSections
                    report={turn.report}
                    snapshot={turn.snapshot}
                    streamingS4={turn.streamingS4}
                    streamPhase={turn.streamPhase}
                    inquiryQuery={
                      i > 0 && turns[i - 1]?.role === "user" ? turns[i - 1].text : ""
                    }
                    insightView={insightView}
                    onInsightViewChange={setInsightView}
                    braidFocusRef={braidFocusRef}
                    onBraidFocusRef={onBraidFocusRef}
                  />
                ) : null}
              </div>
            ))
          )}
        </div>
        {lastReport && !running ? (
          <LogosResearchAskPostFeedbackStrip queryId={lastReport.generated_at_utc?.slice(0, 19) ?? null} />
        ) : null}
        <div className="lr-ask-composer" id="lr-ask-composer">
          <LogosResearchAskQuotaBar refreshKey={quotaRefresh} />
          <div id="lr-ask-samples-anchor" />
          {sampleQuestions.length && (turns.length > 0 || !onboardingOpen) ? (
            <div className="lr-ask-samples" role="group" aria-label="예시 질문">
              {sampleQuestions.map((sample) => (
                <button
                  key={sample}
                  type="button"
                  className="lr-ask-sample-chip"
                  disabled={running}
                  onClick={() => pickSampleQuestion(sample)}
                >
                  {sample}
                </button>
              ))}
            </div>
          ) : null}
          <textarea
            ref={inputRef}
            className="lr-studio-textarea lr-ask-input"
            rows={1}
            placeholder={placeholder}
            value={question}
            onChange={(e) => {
              setQuestion(e.target.value);
              adjustInputHeight();
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void submit();
              }
            }}
            disabled={running}
          />
          <div className="lr-ask-actions">
            <button
              type="button"
              className="lr-btn lr-btn-primary"
              onClick={() => void submit()}
              disabled={running || !question.trim()}
            >
              {running ? runningLabel : runLabel}
            </button>
            {lastReport ? (
              <button type="button" className="lr-btn lr-btn-ghost" onClick={exportJson}>
                {exportLabel}
              </button>
            ) : null}
            <a className="lr-btn lr-btn-ghost" href={handoffUrl} target="_blank" rel="noopener noreferrer">
              {handoffLabel}
            </a>
          </div>
          {paymentUiEnabled ? (
            <div className="lr-ask-pro-checkout" aria-label="Logos Pro 결제 (beta)">
              <p className="lr-ask-muted">Logos Inquiry Pro · 연구 모드 · beta</p>
              <div className="lr-ask-pro-row">
                <input
                  type="email"
                  className="lr-ask-pro-email"
                  placeholder="이메일 (결제 영수)"
                  value={checkoutEmail}
                  onChange={(e) => setCheckoutEmail(e.target.value)}
                  disabled={checkoutBusy}
                />
                <button
                  type="button"
                  className="lr-btn lr-btn-ghost"
                  disabled={checkoutBusy || !checkoutEmail.trim()}
                  onClick={() => void startProCheckout()}
                >
                  {checkoutBusy ? "처리 중…" : "Pro 시작 (beta)"}
                </button>
              </div>
              {checkoutNote ? <p className="lr-ask-muted lr-ask-pro-note">{checkoutNote}</p> : null}
            </div>
          ) : null}
        </div>
      </div>

      <aside
        id="lr-ask-heart-rail"
        className={`lr-ask-heart-rail${heartDrawerOpen ? " lr-ask-heart-rail--open" : ""}`}
        data-lr-ask-heart-rail="1"
        aria-label="출처·통제 · Logos 심장"
      >
        <header className="lr-ask-heart-rail-head">
          <p className="lr-ask-heart-rail-eyebrow">Trust pin · JEMA</p>
          <h2 className="lr-ask-heart-rail-title">출처 · 통제 · 연구 지도</h2>
          <button
            type="button"
            className="lr-btn lr-btn-ghost lr-ask-heart-drawer-close"
            onClick={() => setHeartDrawerOpen(false)}
          >
            닫기
          </button>
        </header>
        {heartSource ? (
          <AskHeartPinStack
            report={heartSource.turn.report}
            snapshot={heartSource.turn.snapshot}
            streamingS4={heartSource.turn.streamingS4}
            streamPhase={heartSource.turn.streamPhase}
            inquiryQuery={heartSource.userQuery}
            scholarMode={insightView === "scholar"}
            braidFocusRef={braidFocusRef}
            onBraidFocusRef={onBraidFocusRef}
          />
        ) : (
          <div className="lr-ask-heart-empty-stack" data-lr-ask-heart-empty="1">
            <p className="lr-ask-muted lr-ask-heart-placeholder">
              답변 후 Citation · G0–G3 · 경로가 여기 고정됩니다.
            </p>
            <LogosAskEmptyResearchMapV1 />
          </div>
        )}
      </aside>
    </div>
  );
}
