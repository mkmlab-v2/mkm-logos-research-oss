"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ClinicianChartPastePanel } from "@/components/ClinicianChartPastePanel";
import { ClinicianCopilotCardsView } from "@/components/ClinicianCopilotCardsView";
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
  disabled,
}: ClinicianEncounterGoldPanelProps) {
  const [lookup, setLookup] = useState(defaultSlug);
  const [chartText, setChartText] = useState("");
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
  const [showDeliverables, setShowDeliverables] = useState(false);

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

  const loadArtifacts = useCallback(async () => {
    const q = lookup.trim();
    if (!q) {
      setError("slug · ref_token · 환자 이름 중 하나를 입력하세요.");
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

  async function runPasteChartAnalysis() {
    const text = chartText.trim();
    if (!text) {
      setError("EMR·차트·상담 메모를 붙여넣으세요.");
      return;
    }
    const q = lookup.trim() || payload?.slug || defaultSlug.trim();
    if (!q) {
      setError("먼저 환자 식별자를 검증하세요.");
      return;
    }

    setAnalyzeBusy(true);
    setError(null);
    setAdvice(null);
    setAdviceWarning(null);
    setFusionMarkdown(null);
    try {
      const body: Record<string, unknown> = {
        schema: "clinician_paste_chart_request_v1",
        chart_text: text,
        options: { validate_schema: true, validate_policy: true, render_md: true },
        ...patientLookupBody(q, payload?.slug),
      };
      if (objectiveDraft.trim()) body.objective_draft = objectiveDraft.trim();
      if (birthInstantUtc.trim()) {
        body.birth_instant_utc = birthInstantUtc.trim();
        body.iana_tz = ianaTz.trim() || "Asia/Seoul";
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
        patient_care_bundle?: Record<string, unknown>;
        patient_facing_markdown?: string;
        advice?: PasteChartAdvice | null;
      };
      if (!res.ok || !json.success || !json.patient_care_bundle) {
        setFusionBundle(null);
        setError(json.error || "Paste Chart 분석에 실패했습니다.");
        return;
      }
      setFusionBundle(json.patient_care_bundle);
      setFusionMarkdown(json.patient_facing_markdown || null);
      setAdvice(json.advice || null);
      if (json.advice_error) {
        setAdviceWarning(`SOAP는 생성됨 · 조언 체인: ${json.advice_error}`);
      }
      onFusionBundleReady?.(json.patient_care_bundle);
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
    <div className="encounter-gold-panel card" aria-labelledby="paste-chart-title">
      <h3 id="paste-chart-title">Paste Chart v1</h3>
      <p className="workspace-muted">
        EMR에서 차트·메모를 복사해 붙여넣기 → SOAP 초안 + 한의 조언. Track B · 로컬 SSOT · EMR 직접 기록 없음.
      </p>

      <div className="encounter-gold-picker">
        <label className="workspace-field-label" htmlFor="paste-chart-lookup">
          환자 식별 (slug / ref_token / 이름)
        </label>
        <div className="encounter-gold-picker-row">
          <input
            id="paste-chart-lookup"
            className="workspace-input"
            value={lookup}
            onChange={(e) => setLookup(e.target.value)}
            placeholder="lee_heecheol · LEE-HEECHEOL-2026-001 · 이희철"
            disabled={disabled || busy}
          />
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => void loadArtifacts()}
            disabled={disabled || busy}
          >
            {busy ? "검증 중…" : "식별자 검증"}
          </button>
        </div>
        {payload?.success ? (
          <p className="consult-source-chip">
            {payload.display_label} · {payload.ref_token} · slug={payload.slug}
          </p>
        ) : null}
      </div>

      {error ? <p className="consult-error">{error}</p> : null}
      {adviceWarning ? <p className="workspace-muted">{adviceWarning}</p> : null}

      <div className="encounter-gold-intake">
        <label className="workspace-field-label" htmlFor="paste-chart-text">
          EMR · 차트 · 상담 메모 붙여넣기
        </label>
        <textarea
          id="paste-chart-text"
          className="workspace-textarea encounter-gold-intake-text"
          rows={10}
          value={chartText}
          onChange={(e) => setChartText(e.target.value)}
          placeholder="EMR S/O/A/P·진료 메모·카톡 상담을 그대로 붙여넣으세요."
          disabled={disabled || analyzeBusy}
        />
        <details className="paste-chart-objective-details">
          <summary>O · 객관 초안 (선택)</summary>
          <textarea
            className="workspace-textarea"
            rows={2}
            value={objectiveDraft}
            onChange={(e) => setObjectiveDraft(e.target.value)}
            placeholder="맥·설진 스태프 메모"
            disabled={disabled || analyzeBusy}
          />
        </details>
        <div className="section-cta" style={{ marginTop: "0.5rem" }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void runPasteChartAnalysis()}
            disabled={disabled || analyzeBusy || busy}
          >
            {analyzeBusy ? "분석 중…" : "분석"}
          </button>
        </div>
      </div>

      {chartSections.length > 0 || advice ? (
        <div className="paste-chart-results">
          {chartSections.length > 0 ? (
            <div className="paste-chart-results-soap">
              <h4>SOAP · EMR 슬롯 복사</h4>
              <ClinicianChartPastePanel sections={chartSections} disabled={disabled} />
            </div>
          ) : null}
          {advice ? (
            <div className="paste-chart-results-advice">
              <h4>한의 조언 · 환자 안내</h4>
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
        <div className="notice-box" role="status">
          <strong>분석 후 SOAP·조언이 여기에 표시됩니다</strong>
          <p className="workspace-muted" style={{ marginTop: "0.35rem" }}>
            환자 식별 검증 → 차트 붙여넣기 → 「분석」 한 번으로 fusion SOAP + IWS 조언 카드를 받습니다.
          </p>
        </div>
      )}

      <details
        className="paste-chart-deliverables-details"
        open={showDeliverables}
        onToggle={(e) => setShowDeliverables((e.target as HTMLDetailsElement).open)}
      >
        <summary>교부물 · 인쇄 · 카톡 (더보기)</summary>
        {fusionMarkdown ? (
          <div className="consult-bundle-md-preview" tabIndex={0} style={{ marginTop: "0.75rem" }}>
            <h5>환자면 MD 미리보기</h5>
            <pre>{fusionMarkdown.slice(0, 3000)}</pre>
          </div>
        ) : null}
        {payload?.success ? (
          <div className="section-cta" style={{ marginTop: "0.5rem" }}>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => void regenerateDeliverables()}
              disabled={disabled || deliverablesBusy || analyzeBusy || busy}
            >
              {deliverablesBusy ? "교부물 갱신 중…" : "생활관리 인쇄 HTML 재생성"}
            </button>
          </div>
        ) : null}
        {kakaoDraftRel ? (
          <p className="consult-source-chip">카톡 드래프트: {kakaoDraftRel}</p>
        ) : null}
        {payload?.success ? (
          <div className="encounter-gold-artifacts">
            <div className="encounter-gold-artifact-grid">
              {payload.artifacts?.map((artifact) => (
                <section key={artifact.key} className="encounter-gold-artifact-card">
                  <h5>{ARTIFACT_LABELS[artifact.key] || artifact.key}</h5>
                  <p className="workspace-muted chart-paste-hint">{artifact.rel_path}</p>
                  {!artifact.exists ? (
                    <p className="workspace-muted">파일 없음</p>
                  ) : artifact.content ? (
                    <pre className="chart-paste-pre encounter-gold-preview">{artifact.content.slice(0, 1200)}</pre>
                  ) : null}
                  {artifact.exists && artifact.content ? (
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => void copyArtifact(artifact.key, artifact.content || "")}
                    >
                      {copyOk === artifact.key ? "복사됨 ✓" : "복사"}
                    </button>
                  ) : null}
                </section>
              ))}
            </div>
            <div className="section-cta" style={{ marginTop: "0.75rem" }}>
              {kakaoMd?.content ? (
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => void copyArtifact("clinic_kakao", kakaoMd.content || "")}
                >
                  카톡 텍스트 복사
                </button>
              ) : null}
              {payload.print_html_rel ? (
                <button type="button" className="btn btn-ghost" onClick={openPrintHtml}>
                  생활관리 인쇄 (HTML)
                </button>
              ) : null}
            </div>
          </div>
        ) : (
          <p className="workspace-muted">환자 식별 검증 후 로컬 교부물을 불러옵니다.</p>
        )}
      </details>
    </div>
  );
}
