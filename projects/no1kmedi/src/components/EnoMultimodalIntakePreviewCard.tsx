"use client";

import { useState } from "react";
import type { ClinicianThreadContext } from "@/lib/clinician-chat-types";
import {
  ENO_HEALTH_INTAKE_STORAGE_KEY,
  applyEnoIntakeToClinicianNotes,
  type EnoMultimodalIntakeSnapshot,
} from "@/lib/eno-multimodal-intake-v1";

type EnoMultimodalIntakePreviewCardProps = {
  context: ClinicianThreadContext;
  onContextChange: (patch: Partial<ClinicianThreadContext>) => void;
};

function trafficClass(status: EnoMultimodalIntakeSnapshot["traffic_light"]["status"]): string {
  if (status === "high_risk") return "triage-badge triage-badge-emergency";
  if (status === "caution") return "triage-badge triage-badge-priority";
  return "triage-badge triage-badge-routine";
}

export function EnoMultimodalIntakePreviewCard({ context, onContextChange }: EnoMultimodalIntakePreviewCardProps) {
  const [jsonDraft, setJsonDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [preview, setPreview] = useState<EnoMultimodalIntakeSnapshot | null>(context.enoMultimodalIntake ?? null);

  async function loadPreview(source: "paste_json" | "local_storage", payload: unknown) {
    setBusy(true);
    setStatus("");
    try {
      const res = await fetch("/api/clinician/eno-multimodal-intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload, source, include_guardian_analysis: true }),
      });
      const json = (await res.json()) as { success?: boolean; error?: string; preview?: EnoMultimodalIntakeSnapshot };
      if (!res.ok || !json.success || !json.preview) {
        setStatus(json.error === "empty_channels" ? "음성·설진·설문·rPPG 중 하나 이상 필요합니다." : "미리보기 실패");
        return;
      }
      setPreview(json.preview);
      setStatus("미리보기 완료 — 「진료 맥락에 반영」으로 적용하세요.");
    } catch {
      setStatus("네트워크 오류");
    } finally {
      setBusy(false);
    }
  }

  async function previewFromPaste() {
    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonDraft);
    } catch {
      setStatus("JSON 형식이 올바르지 않습니다.");
      return;
    }
    await loadPreview("paste_json", parsed);
  }

  async function previewFromLocalSession() {
    try {
      const raw = localStorage.getItem(ENO_HEALTH_INTAKE_STORAGE_KEY);
      if (!raw) {
        setStatus(`로컬 세션 키(${ENO_HEALTH_INTAKE_STORAGE_KEY})가 없습니다.`);
        return;
      }
      await loadPreview("local_storage", JSON.parse(raw));
    } catch {
      setStatus("로컬 세션 JSON을 읽지 못했습니다.");
    }
  }

  function applyToContext() {
    if (!preview) {
      setStatus("먼저 미리보기를 실행하세요.");
      return;
    }
    onContextChange({
      enoMultimodalIntake: preview,
      constitutionFreeText: applyEnoIntakeToClinicianNotes(context.constitutionFreeText, preview),
    });
    setStatus("진료 맥락에 반영됨 (변증 메모·CDSS 보조 입력). 최종 확정은 한의사.");
  }

  return (
    <div className="card consult-access-card">
      <h3>엔오 멀티모달 intake (보조)</h3>
      <p className="workspace-muted">
        엔오헬스케어 PWA(음성·설진·설문·rPPG) 관측을 진료 전에 구조화합니다. <strong>진단·처방 아님</strong> — 원장
        확인 후 CDSS·번들에 반영.
      </p>
      <p className="workspace-muted">
        동일 출처 PWA는 <code>localStorage[{ENO_HEALTH_INTAKE_STORAGE_KEY}]</code>에 JSON을 두면 불러올 수 있습니다.
      </p>
      <textarea
        className="eno-intake-json-draft"
        rows={4}
        value={jsonDraft}
        onChange={(e) => setJsonDraft(e.target.value)}
        placeholder='{"health_data":{"survey":{"vector_4d":{"S":0.25,"L":0.25,"K":0.25,"M":0.25}},"voice":{"jitter":0.2}}}'
        spellCheck={false}
      />
      <div className="consult-access-row">
        <button type="button" className="btn btn-ghost" onClick={() => void previewFromPaste()} disabled={busy}>
          {busy ? "처리 중…" : "JSON 미리보기"}
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => void previewFromLocalSession()} disabled={busy}>
          로컬 세션 불러오기
        </button>
        <button type="button" className="btn btn-primary" onClick={applyToContext} disabled={!preview || busy}>
          진료 맥락에 반영
        </button>
      </div>
      {status ? (
        <p className={status.includes("반영") || status.includes("완료") ? "consult-access-ok" : "consult-error"}>{status}</p>
      ) : null}
      {preview ? (
        <div className="eno-intake-preview-block">
          <p className="consult-source-chip">
            <span className={trafficClass(preview.traffic_light.status)}>
              {preview.traffic_light.icon} {preview.traffic_light.status}
            </span>{" "}
            · {preview.clinician_summary_ko}
          </p>
          {preview.guardian_analysis_message ? (
            <p className="workspace-muted">
              <strong>가디언 초안:</strong> {preview.guardian_analysis_message}
            </p>
          ) : null}
          <p className="workspace-muted">{preview.disclaimer_ko}</p>
        </div>
      ) : context.enoMultimodalIntake ? (
        <p className="consult-source-chip">{context.enoMultimodalIntake.clinician_summary_ko}</p>
      ) : null}
    </div>
  );
}
