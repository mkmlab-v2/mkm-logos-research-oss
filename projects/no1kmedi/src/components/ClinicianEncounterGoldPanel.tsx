"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ClinicianChartPastePanel } from "@/components/ClinicianChartPastePanel";
import { ClinicianCopilotCardsView } from "@/components/ClinicianCopilotCardsView";
import { PasteChartOmniBox } from "@/components/PasteChartOmniBox";
import { PASTE_CHART_PUBLIC_COPY_V1 } from "@/lib/paste-chart-public-copy-v1";
import {
  birthdateToBirthInstantUtc,
  type PasteExtractDraftV1,
} from "@/lib/clinician-chart-paste-extract-v1";
import {
  buildChartPasteSectionsFromBundle,
  buildChartPasteSectionsFromCdsDraft,
  buildChartPasteSectionsFromSoapStub,
  mergeChartPasteSections,
} from "@/lib/clinician-chart-paste-sections-v1";
import type {
  SimpleCopilotCardsV1,
  SimpleCopilotMedicalCalcV1,
  SimpleCopilotSajuCalcV1,
} from "@/lib/clinician-simple-copilot-v1";

type EncounterArtifactsResponse = {
  success: boolean;
  error?: string;
  slug?: string;
  display_label?: string;
  ref_token?: string;
  artifacts?: Array<{
    key: string;
    rel_path: string;
    exists: boolean;
    content?: string;
    truncated?: boolean;
  }>;
  print_html_rel?: string | null;
  boundary_ko?: string;
};

type PasteChartAdvice = {
  cards: SimpleCopilotCardsV1;
  medical_calc: SimpleCopilotMedicalCalcV1;
  saju_calc: SimpleCopilotSajuCalcV1;
  patient_education_copy: string;
};

import type { PasteChartSessionSyncV1 } from "@/lib/clinician-paste-chart-fusion-v1";

export type { PasteChartSessionSyncV1 };

type ClinicianEncounterGoldPanelProps = {
  clinicianEmail?: string;
  defaultSlug?: string;
  birthInstantUtc?: string;
  ianaTz?: string;
  cdsDraft?: {
    request_id: string;
    clinical_summary: string;
    reasoning: { syndrome_hypothesis: string; care_direction: string; caution: string };
  } | null;
  patientCareBundle?: Record<string, unknown> | null;
  onFusionBundleReady?: (bundle: Record<string, unknown>) => void;
  onPasteChartSession?: (session: PasteChartSessionSyncV1) => void;
  disabled?: boolean;
};

const ARTIFACT_LABELS: Record<string, string> = {
  lifestyle_management_md: "생활관리 가이드 (Markdown)",
  clinic_kakao: "카톡 발송용 텍스트",
  patient_comprehensive_guide: "환자 종합 처방전",
  physician_comprehensive_guide: "원장 종합 처방전",
};

function clinicianHeaders(email?: string): HeadersInit {
  const h: HeadersInit = {};
  const e = email?.trim().toLowerCase();
  if (e) h["x-clinician-email"] = e;
  return h;
}

function isEphemeralEncounterSlug(value: string): boolean {
  return value.trim().toLowerCase().startsWith("ephemeral_");
}

function humanGoldLookupSeed(defaultSlug: string): string {
  const s = defaultSlug.trim();
  return isEphemeralEncounterSlug(s) ? "" : s;
}

function patientLookupBody(q: string, payloadSlug?: string): Record<string, string> {
  if (payloadSlug) return { slug: payloadSlug };
  if (/^[A-Z0-9-]+$/i.test(q) && q.includes("-")) return { ref_token: q };
  if (/^[a-z][a-z0-9_]*$/i.test(q) && q.includes("_")) return { slug: q };
  return { display: q };
}

export function ClinicianEncounterGoldPanel({
  clinicianEmail,
  defaultSlug = "",
  birthInstantUtc = "",
  ianaTz = "Asia/Seoul",
  cdsDraft,
  patientCareBundle,
  onFusionBundleReady,
  onPasteChartSession,
  disabled,
}: ClinicianEncounterGoldPanelProps) {
  const [lookup, setLookup] = useState(() => humanGoldLookupSeed(defaultSlug));
  const [chartText, setChartText] = useState("");
  const [extractDraft, setExtractDraft] = useState<PasteExtractDraftV1>({
    schema: "paste_extract_draft_v1",
    confidence: "low",
    sources: [],
  });
  const [objectiveDraft, setObjectiveDraft] = useState("");
  const [analyzeBusy, setAnalyzeBusy] = useState(false);
  const [deliverablesBusy, setDeliverablesBusy] = useState(false);
  const [fusionBundle, setFusionBundle] = useState<Record<string, unknown> | null>(null);
  const [fusionMarkdown, setFusionMarkdown] = useState<string | null>(null);
  const [advice, setAdvice] = useState<PasteChartAdvice | null>(null);
  const [adviceWarning, setAdviceWarning] = useState<string | null>(null);
  const [kakaoDraftRel, setKakaoDraftRel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<EncounterArtifactsResponse | null>(null);
  const [copyOk, setCopyOk] = useState<string | null>(null);
  const [ephemeralEncounter, setEphemeralEncounter] = useState(false);

  useEffect(() => {
    const s = defaultSlug.trim();
    if (!s || isEphemeralEncounterSlug(s)) return;
    setLookup((cur) => (cur.trim() ? cur : s));
  }, [defaultSlug]);

  const chartSections = useMemo(() => {
    const fromDraft = cdsDraft ? buildChartPasteSectionsFromCdsDraft(cdsDraft) : [];
    const fromBundle = patientCareBundle ? buildChartPasteSectionsFromBundle(patientCareBundle) : [];
    const fromFusionBundle = fusionBundle ? buildChartPasteSectionsFromBundle(fusionBundle) : [];
    const fromFusionSoap =
      fusionBundle?.clinical_soap_v1 && typeof fusionBundle.clinical_soap_v1 === "object"
        ? buildChartPasteSectionsFromSoapStub(fusionBundle.clinical_soap_v1 as Record<string, { text?: string }>)
        : [];
    return mergeChartPasteSections(fromFusionSoap, fromFusionBundle, fromDraft, fromBundle);
  }, [cdsDraft, patientCareBundle, fusionBundle]);

  const hasResults = chartSections.length > 0 || Boolean(advice);

  const loadArtifacts = useCallback(async () => {
    const q = lookup.trim();
    if (!q) {
      setError("slug · ref_token · 환자 이름 중 하나를 입력하세요.");
      return;
    }
    if (isEphemeralEncounterSlug(q)) {
      setError(
        "1회성 encounter(ephemeral_…)는 Human Gold 검증 대상이 아닙니다. 차트 붙여넣기 → 「분석」만 사용하세요.",
      );
      return;
    }
    setBusy(true);
    setError(null);
    setCopyOk(null);
    try {
      const params = new URLSearchParams(patientLookupBody(q));
      const res = await fetch(`/api/clinician/encounter-artifacts?${params}`, {
        headers: clinicianHeaders(clinicianEmail),
      });
      const json = (await res.json()) as EncounterArtifactsResponse;
      if (!res.ok || !json.success) {
        setPayload(null);
        setError(json.error || "환자 SSOT를 찾지 못했습니다.");
        return;
      }
      setPayload(json);
    } catch {
      setPayload(null);
      setError("네트워크 오류 — MKM_WORKSPACE_ROOT와 서버 로그를 확인하세요.");
    } finally {
      setBusy(false);
    }
  }, [clinicianEmail, lookup]);

  function resolveBirthInstantForRequest(): string {
    const fromChip = extractDraft.birthdate
      ? birthdateToBirthInstantUtc(extractDraft.birthdate, ianaTz.trim() || "Asia/Seoul")
      : null;
    if (fromChip) return fromChip;
    if (birthInstantUtc.trim()) return birthInstantUtc.trim();
    return "";
  }

  function resolvePatientLookup(): Record<string, string> | null {
    const slugCandidate =
      payload?.slug ||
      (!isEphemeralEncounterSlug(defaultSlug) ? defaultSlug.trim() : "") ||
      (lookup.trim().includes("_") && !isEphemeralEncounterSlug(lookup) ? lookup.trim() : "");
    if (slugCandidate && /^[a-z][a-z0-9_]*$/i.test(slugCandidate)) {
      return patientLookupBody(slugCandidate, payload?.slug);
    }
    const refQ = lookup.trim();
    if (refQ && refQ.includes("-") && /^[A-Z0-9-]+$/i.test(refQ)) {
      return patientLookupBody(refQ, payload?.slug);
    }
    const display =
      extractDraft.display_name?.trim() ||
      payload?.display_label?.trim() ||
      (lookup.trim() && !lookup.includes("_") ? lookup.trim() : "");
    if (display) return { display };
    return null;
  }

  function friendlyPasteChartError(code?: string): string {
    if (!code) return "Paste Chart 분석에 실패했습니다.";
    if (code === "unauthorized") {
      return "Pro 권한 이메일이 필요합니다. 「환자·설정」에서 등록 이메일 입력·확인 후 다시 시도하거나 URL에 ?email= 을 추가하세요.";
    }
    if (code.startsWith("unknown_display")) {
      return "이름·생년 칩을 확인해 주세요. Human Gold 환자는 고급에서 slug 연결도 가능합니다.";
    }
    if (code.includes("birth_profile_missing")) {
      return "생년월일을 칩에서 확인·수정해 주세요. ISO 타임스탬프 직접 입력은 필요 없습니다.";
    }
    if (code.startsWith("slug_ref_token_or_display_required")) {
      return "차트에서 이름을 추출하지 못했습니다. 이름 칩을 수정하거나 고급에서 slug를 연결하세요.";
    }
    if (code.startsWith("unknown_slug:ephemeral_")) {
      return "1회성 encounter는 Human Gold slug가 아닙니다. 고급 slug 칸을 비우고 차트 붙여넣기 → 「분석」을 사용하세요.";
    }
    return code;
  }

  async function runPasteChartAnalysis() {
    const text = chartText.trim();
    if (!text) {
      setError("EMR·차트·상담 메모를 붙여넣으세요.");
      return;
    }
    if (!clinicianEmail?.trim()) {
      setError(
        "Pro 권한 이메일이 없습니다. 「환자·설정」 탭에서 이메일을 입력·확인하거나 URL에 ?email=your@email 을 추가하세요.",
      );
      return;
    }
    const lookupBody = resolvePatientLookup();
    if (!lookupBody) {
      setError("이름을 칩에서 확인하거나, 고급에서 Human Gold slug를 연결하세요.");
      return;
    }
    const birthIso = resolveBirthInstantForRequest();
    const hasSlug = "slug" in lookupBody || "ref_token" in lookupBody;
    if (!hasSlug && !birthIso) {
      setError("익명 1회 분석에는 생년월일 칩 확인이 필요합니다.");
      return;
    }

    setAnalyzeBusy(true);
    setError(null);
    setAdvice(null);
    setAdviceWarning(null);
    setFusionMarkdown(null);
    setEphemeralEncounter(false);
    try {
      const body: Record<string, unknown> = {
        schema: "clinician_paste_chart_request_v1",
        chart_text: text,
        allow_ephemeral: true,
        options: { validate_schema: true, validate_policy: false, render_md: true },
        ...lookupBody,
      };
      if (objectiveDraft.trim()) body.objective_draft = objectiveDraft.trim();
      if (birthIso) {
        body.birth_instant_utc = birthIso;
        body.iana_tz = ianaTz.trim() || "Asia/Seoul";
        if (extractDraft.sex === "M") body.is_male = true;
        if (extractDraft.sex === "F") body.is_male = false;
      }

      const res = await fetch("/api/clinician/paste-chart-v1", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...clinicianHeaders(clinicianEmail) },
        body: JSON.stringify(body),
      });
      const json = (await res.json()) as {
        success?: boolean;
        error?: string;
        advice_error?: string;
        slug?: string;
        display_label?: string;
        ephemeral?: boolean;
        patient_care_bundle?: Record<string, unknown>;
        patient_facing_markdown?: string;
        advice?: PasteChartAdvice | null;
      };
      if (!res.ok || !json.success || !json.patient_care_bundle) {
        setFusionBundle(null);
        setError(friendlyPasteChartError(json.error));
        return;
      }
      setFusionBundle(json.patient_care_bundle);
      setFusionMarkdown(json.patient_facing_markdown || null);
      setAdvice(json.advice || null);
      setEphemeralEncounter(Boolean(json.ephemeral));
      if (json.advice_error) {
        setAdviceWarning(`SOAP는 생성됨 · 조언 체인: ${json.advice_error}`);
      }
      if (json.ephemeral) {
        setAdviceWarning((prev) =>
          prev
            ? `${prev} · 1회성 익명 encounter (Human Gold 미연결)`
            : "1회성 익명 encounter — Human Gold 교부물·slug 검증 없음",
        );
      }
      onFusionBundleReady?.(json.patient_care_bundle);

      const patientLabel =
        extractDraft.display_name?.trim() || json.display_label?.trim() || lookup.trim() || "환자";
      const soap = json.patient_care_bundle.clinical_soap_v1 as
        | Record<string, { text?: string }>
        | undefined;
      const summarySnippet =
        soap?.assessment?.text?.trim() ||
        soap?.subjective?.text?.trim()?.slice(0, 120) ||
        extractDraft.chief_complaint?.trim() ||
        "Paste Chart 분석 완료";
      const adviceTitles =
        json.advice?.cards?.tcm_primary?.items?.map((item) => String(item.title || "").trim()).filter(Boolean) ||
        [];
      const assessmentLine = soap?.assessment?.text?.split("\n").find((l) => l.includes("체질"))?.trim();
      onPasteChartSession?.({
        patientLabel,
        title: patientLabel,
        chartSnippet: text.slice(0, 500),
        summarySnippet: summarySnippet.slice(0, 280),
        birthInstantUtc: birthIso || undefined,
        ianaTz: ianaTz.trim() || "Asia/Seoul",
        chiefComplaint: extractDraft.chief_complaint?.trim(),
        slug: json.slug || payload?.slug || defaultSlug.trim() || undefined,
        adviceTitles,
        assessmentLine,
        ephemeral: Boolean(json.ephemeral),
      });
    } catch {
      setFusionBundle(null);
      setError("네트워크 오류 — Python 체인·MKM_WORKSPACE_ROOT를 확인하세요.");
    } finally {
      setAnalyzeBusy(false);
    }
  }

  async function regenerateDeliverables() {
    const q = lookup.trim() || payload?.slug || defaultSlug.trim();
    if (!q && !payload?.slug) {
      setError("먼저 환자 식별자를 검증하세요.");
      return;
    }
    setDeliverablesBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        schema: "clinician_encounter_lifestyle_deliverables_request_v1",
        write_kakao_draft: Boolean(fusionMarkdown?.trim()),
        ...patientLookupBody(q, payload?.slug),
      };
      if (fusionMarkdown?.trim()) body.fusion_markdown = fusionMarkdown.trim();

      const res = await fetch("/api/clinician/encounter-lifestyle-deliverables-v1", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...clinicianHeaders(clinicianEmail) },
        body: JSON.stringify(body),
      });
      const json = (await res.json()) as {
        success?: boolean;
        error?: string;
        paths?: { kakao_draft?: string; print_html?: string };
      };
      if (!res.ok || !json.success) {
        setError(json.error || "교부물 인쇄 HTML 재생성에 실패했습니다.");
        return;
      }
      setKakaoDraftRel(json.paths?.kakao_draft || null);
      await loadArtifacts();
    } catch {
      setError("네트워크 오류 — render 스크립트·fixture JSON을 확인하세요.");
    } finally {
      setDeliverablesBusy(false);
    }
  }

  useEffect(() => {
    if (defaultSlug.trim()) void loadArtifacts();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial slug only
  }, []);

  async function copyArtifact(key: string, content: string) {
    if (!content.trim()) return;
    try {
      await navigator.clipboard.writeText(content);
      setCopyOk(key);
      window.setTimeout(() => setCopyOk((c) => (c === key ? null : c)), 2000);
    } catch {
      setError("클립보드 복사에 실패했습니다.");
    }
  }

  function openPrintHtml() {
    if (!payload?.slug) return;
    const url = `/api/clinician/encounter-artifacts/print?slug=${encodeURIComponent(payload.slug)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  const lifestyleMd = payload?.artifacts?.find((a) => a.key === "lifestyle_management_md" && a.exists);
  const kakaoMd = payload?.artifacts?.find((a) => a.key === "clinic_kakao" && a.exists);

  return (
    <div className="encounter-gold-panel paste-chart-v1" aria-labelledby="paste-chart-title">
      <header className="pc-header">
        <div className="pc-header-inner">
          <div className="pc-brand">
            <div className="pc-brand-mark" aria-hidden>
              P
            </div>
            <div>
              <h2 id="paste-chart-title" className="pc-brand-name">
                Paste Chart
              </h2>
              <p className="pc-brand-sub">{PASTE_CHART_PUBLIC_COPY_V1.brandSub}</p>
            </div>
          </div>
          <div className="pc-header-meta">
            <span className="track-badge">Track B · 초안</span>
            {ephemeralEncounter ? <span className="track-badge track-badge--ephemeral">1회성 encounter</span> : null}
            <span className="human-gold-badge">Human Gold 확정 필요</span>
          </div>
        </div>
      </header>

      <main className="paste-chart-shell">
        <PasteChartOmniBox
          chartText={chartText}
          onChartTextChange={setChartText}
          draft={extractDraft}
          onDraftChange={setExtractDraft}
          objectiveDraft={objectiveDraft}
          onObjectiveDraftChange={setObjectiveDraft}
          onAnalyze={() => void runPasteChartAnalysis()}
          analyzeBusy={analyzeBusy}
          disabled={disabled || busy}
          error={error}
          adviceWarning={adviceWarning}
          clinicianEmail={clinicianEmail}
          advancedSlot={
            <>
              <div className="pc-patient-row">
                <div className="pc-patient-field">
                  <label htmlFor="paste-chart-lookup">slug · ref_token · 이름 (SSOT)</label>
                  <input
                    id="paste-chart-lookup"
                    type="text"
                    className="pc-input"
                    value={lookup}
                    onChange={(e) => setLookup(e.target.value)}
                    placeholder="lee_heecheol · REF-… · 환자 이름"
                    disabled={disabled || busy}
                    autoComplete="off"
                  />
                </div>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => void loadArtifacts()}
                  disabled={disabled || busy}
                >
                  {busy ? "검증 중…" : "Human Gold 검증"}
                </button>
              </div>
              {payload?.success ? (
                <div className="patient-chip-row">
                  <span className="patient-chip">
                    <span className="chip-dot" aria-hidden />
                    {payload.display_label}
                  </span>
                  <span className="chip-sep">·</span>
                  <span className="patient-chip">{payload.ref_token}</span>
                  <span className="chip-sep">·</span>
                  <span className="patient-chip">slug={payload.slug}</span>
                  <span className="chip-ok">✓ 검증됨</span>
                </div>
              ) : (
                <p className="paste-chart-muted">연구·Human Gold 케이스만 slug 검증이 필요합니다.</p>
              )}
            </>
          }
        />

        {hasResults ? (
          <div className="pc-results-grid">
            {chartSections.length > 0 ? (
              <ClinicianChartPastePanel sections={chartSections} disabled={disabled} variant="paste-chart" />
            ) : null}
            {advice ? (
              <div className="advice-panel">
                <div className="advice-panel-head">
                  <h4 className="advice-panel-title">한의 조언 · 환자 안내</h4>
                </div>
                <ClinicianCopilotCardsView
                  cards={advice.cards}
                  medicalCalc={advice.medical_calc}
                  sajuCalc={advice.saju_calc}
                  chiefComplaint={chartText.trim().split("\n")[0] || ""}
                  patientEducationCopy={advice.patient_education_copy}
                  compact
                />
              </div>
            ) : null}
          </div>
        ) : (
          <div className="paste-chart-empty" role="status">
            <strong>분석 후 SOAP·조언이 여기에 표시됩니다</strong>
            <p>차트 통째 붙여넣기 → 칩 확인 → 「분석」 한 번</p>
          </div>
        )}

        <details className="more-details">
          <summary>
            <span className="more-arrow" aria-hidden>
              ▶
            </span>
            교부물 · 인쇄 · 카톡 (더보기)
          </summary>
          <div className="more-body">
            {fusionMarkdown ? (
              <div className="consult-bundle-md-preview paste-chart-md-preview" tabIndex={0}>
                <h5>환자면 MD 미리보기</h5>
                <pre>{fusionMarkdown.slice(0, 3000)}</pre>
              </div>
            ) : null}
            {payload?.success ? (
              <button
                type="button"
                className="more-action-btn"
                onClick={() => void regenerateDeliverables()}
                disabled={disabled || deliverablesBusy || analyzeBusy || busy}
              >
                {deliverablesBusy ? "교부물 갱신 중…" : "생활관리 인쇄 HTML 재생성"}
              </button>
            ) : null}
            {kakaoDraftRel ? <span className="patient-chip">카톡 드래프트: {kakaoDraftRel}</span> : null}
            {kakaoMd?.content ? (
              <button
                type="button"
                className="more-action-btn"
                onClick={() => void copyArtifact("clinic_kakao", kakaoMd.content || "")}
              >
                {copyOk === "clinic_kakao" ? "카톡 복사됨 ✓" : "카톡 텍스트 복사"}
              </button>
            ) : null}
            {payload?.print_html_rel ? (
              <button type="button" className="more-action-btn" onClick={openPrintHtml}>
                생활관리 인쇄 (HTML)
              </button>
            ) : null}
            {lifestyleMd?.content ? (
              <button
                type="button"
                className="more-action-btn"
                onClick={() => void copyArtifact("lifestyle_management_md", lifestyleMd.content || "")}
              >
                {copyOk === "lifestyle_management_md" ? "MD 복사됨 ✓" : "생활관리 MD 복사"}
              </button>
            ) : null}
          </div>
          {payload?.success ? (
            <div className="encounter-gold-artifact-grid paste-chart-artifact-grid">
              {payload.artifacts?.map((artifact) => (
                <section key={artifact.key} className="encounter-gold-artifact-card">
                  <h5>{ARTIFACT_LABELS[artifact.key] || artifact.key}</h5>
                  <p className="chart-paste-hint">{artifact.rel_path}</p>
                  {!artifact.exists ? (
                    <p className="paste-chart-muted">파일 없음</p>
                  ) : artifact.content ? (
                    <pre className="encounter-gold-preview">{artifact.content.slice(0, 800)}</pre>
                  ) : null}
                </section>
              ))}
            </div>
          ) : (
            <p className="paste-chart-muted more-body-hint">환자 식별 검증 후 로컬 교부물을 불러옵니다.</p>
          )}
        </details>

        <details className="more-details pc-why-not-auto">
          <summary>
            <span className="more-arrow" aria-hidden>
              ▶
            </span>
            {PASTE_CHART_PUBLIC_COPY_V1.whyNotAutoSummary}
          </summary>
          <div className="more-body pc-why-not-auto-body">
            <ul className="pc-why-not-auto-list">
              {PASTE_CHART_PUBLIC_COPY_V1.whyNotAutoBullets.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        </details>

        <footer className="pc-footer-disclaimer">
          <p>{PASTE_CHART_PUBLIC_COPY_V1.footerDisclaimer}</p>
          <p>{PASTE_CHART_PUBLIC_COPY_V1.footerDisclaimerSecondary}</p>
        </footer>
      </main>
    </div>
  );
}
