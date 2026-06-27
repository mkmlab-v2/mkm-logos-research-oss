"use client";

import { useMemo, useState } from "react";
import {
  buildSoapStubFromConsultDraft,
  type ClinicianConsultFormState,
} from "@/lib/clinician-consult-payload-v1";
import { trackKmCdsUiEvent, KM_CDS_UI_ANALYTICS_EVENTS_V1 } from "@/lib/km-cds-ui-analytics-events-v1";

type ConsultDraftSlice = {
  request_id: string;
  clinical_summary: string;
  reasoning: { syndrome_hypothesis: string; care_direction: string; caution: string };
};

type PatientCareBundlePreviewProps = {
  enabled: boolean;
  formState: ClinicianConsultFormState;
  draft: ConsultDraftSlice;
  cdsEnvelope: Record<string, unknown> | undefined;
  kmCdsValidationOk: boolean;
  onBundleReady?: (bundle: Record<string, unknown>) => void;
};

type BundleApiResponse = {
  success: boolean;
  error?: string;
  detail?: string;
  patient_care_bundle?: {
    bundle_id?: string;
    schema?: string;
    disclaimers?: string[];
    patient_slots?: Array<{ slot_id?: string; title?: string; body_markdown?: string; included?: boolean }>;
  };
  patient_facing_markdown?: string;
  boundary?: { physician_confirmation_required?: boolean };
};

function renderBundleMarkdownFallback(bundle: NonNullable<BundleApiResponse["patient_care_bundle"]>): string {
  const lines: string[] = ["# 환자 안내 번들 (미리보기)\n"];
  if (bundle.bundle_id) lines.push(`- bundle_id: \`${bundle.bundle_id}\`\n`);
  lines.push("\n> Track B · 명리·보조 슬롯은 [HYPO]/비임상 참고입니다. 최종 확정은 한의사가 수행합니다.\n\n");
  const slots = [...(bundle.patient_slots || [])].sort(
    (a, b) => Number(a.slot_id?.length || 0) - Number(b.slot_id?.length || 0),
  );
  for (const slot of slots) {
    if (slot.included === false) continue;
    lines.push(`## ${slot.title || slot.slot_id || "slot"}\n\n`);
    lines.push(`${(slot.body_markdown || "").trim()}\n\n`);
  }
  if (bundle.disclaimers?.length) {
    lines.push("## 면책\n\n");
    for (const d of bundle.disclaimers) lines.push(`- ${d}\n`);
  }
  return lines.join("");
}

export function PatientCareBundlePreview({
  enabled,
  formState,
  draft,
  cdsEnvelope,
  kmCdsValidationOk,
  onBundleReady,
}: PatientCareBundlePreviewProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<BundleApiResponse | null>(null);
  const [applyTemplates, setApplyTemplates] = useState(true);
  const [validatePolicy, setValidatePolicy] = useState(true);
  const [renderMd, setRenderMd] = useState(true);

  const previewMarkdown = useMemo(() => {
    if (!response?.success) return "";
    if (response.patient_facing_markdown?.trim()) return response.patient_facing_markdown;
    if (response.patient_care_bundle) return renderBundleMarkdownFallback(response.patient_care_bundle);
    return "";
  }, [response]);

  async function onGenerateBundle() {
    if (!enabled || !cdsEnvelope || !kmCdsValidationOk) {
      setError("CDSS 봉투 검증이 완료된 뒤에만 환자 번들을 생성할 수 있습니다.");
      return;
    }
    setBusy(true);
    setError(null);
    setResponse(null);
    try {
      trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.CDS_BUNDLE_GENERATE_V1, {
        surface: "workspace",
        locale: "ko-KR",
      });
      const res = await fetch("/api/cdss/patient-care-bundle-from-cds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          schema: "patient_care_bundle_from_cds_request_v1",
          request_id: draft.request_id,
          birth_instant_utc: formState.birthInstantUtc.trim(),
          iana_tz: formState.ianaTz.trim(),
          cds_envelope: cdsEnvelope,
          soap: buildSoapStubFromConsultDraft(draft),
          options: {
            apply_slot_templates: applyTemplates,
            validate_policy: validatePolicy,
            validate_bundle: true,
            render_patient_md: renderMd,
          },
        }),
      });
      const json = (await res.json()) as BundleApiResponse & { detail?: string };
      if (!res.ok || !json.success) {
        setError(json.detail || json.error || "환자 번들 생성에 실패했습니다.");
        setResponse(json);
        return;
      }
      setResponse(json);
      if (json.patient_care_bundle) {
        onBundleReady?.(json.patient_care_bundle as Record<string, unknown>);
      }
    } catch {
      setError("환자 번들 생성 중 네트워크 오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function copyPreview() {
    if (!previewMarkdown) return;
    try {
      await navigator.clipboard.writeText(previewMarkdown);
      setError(null);
    } catch {
      setError("미리보기 복사에 실패했습니다.");
    }
  }

  if (!cdsEnvelope) {
    return (
      <div className="consult-bundle-panel notice-box" role="status">
        <strong>환자 안내 번들</strong>
        <p className="workspace-muted" style={{ marginTop: "0.35rem" }}>
          먼저 「진료 보조 초안 생성」을 실행하면 SSOT 봉투가 준비됩니다.
        </p>
      </div>
    );
  }

  return (
    <div className="consult-bundle-panel card" aria-labelledby="patient-bundle-preview-title">
      <h3 id="patient-bundle-preview-title">환자 안내 번들 (내부 · 한의사 확인 전)</h3>
      <p className="workspace-muted">
        CDSS 봉투 + 출생 정보로 `patient_care_bundle_v1`을 생성합니다. 환자 제공·대외 발송 전 반드시 한의사가
        검토·확정하세요. 명리 슬롯은 [HYPO] 참고용입니다.
      </p>
      {!kmCdsValidationOk ? (
        <p className="consult-error">CDSS 봉투 Python 검증이 통과하지 않았습니다. MKM_WORKSPACE_ROOT를 확인하세요.</p>
      ) : null}
      <div className="consult-bundle-options">
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <input type="checkbox" checked={applyTemplates} onChange={(e) => setApplyTemplates(e.target.checked)} />
          슬롯 템플릿 적용
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <input type="checkbox" checked={validatePolicy} onChange={(e) => setValidatePolicy(e.target.checked)} />
          생성 정책 검증
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <input type="checkbox" checked={renderMd} onChange={(e) => setRenderMd(e.target.checked)} />
          Markdown 미리보기
        </label>
      </div>
      <div className="section-cta" style={{ marginTop: "0.75rem" }}>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onGenerateBundle}
          disabled={busy || !enabled || !kmCdsValidationOk}
        >
          {busy ? "번들 생성 중..." : "환자 안내 번들 생성"}
        </button>
        {previewMarkdown ? (
          <button type="button" className="btn btn-ghost" onClick={copyPreview}>
            미리보기 복사
          </button>
        ) : null}
      </div>
      {error ? <p className="consult-error">{error}</p> : null}
      {response?.success && response.patient_care_bundle?.bundle_id ? (
        <p className="consult-source-chip" style={{ marginTop: "0.5rem" }}>
          bundle_id: {response.patient_care_bundle.bundle_id}
        </p>
      ) : null}
      {previewMarkdown ? (
        <div className="consult-bundle-md-preview" tabIndex={0}>
          <pre>{previewMarkdown}</pre>
        </div>
      ) : null}
    </div>
  );
}
