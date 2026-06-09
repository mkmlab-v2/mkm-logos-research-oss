/**
 * Eno multimodal intake → clinician preview (physician_gold lane, human_confirm).
 * B-track observation only — not diagnosis. No auto CDSS merge without clinician apply.
 */

export const ENO_HEALTH_INTAKE_STORAGE_KEY = "eno_health_intake_v1";

export type EnoHealthData = {
  rppg?: {
    heart_rate?: number;
    stress_score?: number;
    signal_quality?: number;
  };
  tongue?: {
    color?: string;
    coating?: string;
    shape?: string;
    moisture?: string;
    hydrationScore?: number;
    healthInsight?: string;
  };
  voice?: {
    pitch?: number;
    jitter?: number;
    shimmer?: number;
    hnr?: number;
  };
  survey?: {
    vector_4d?: { S: number; L: number; K: number; M: number };
    total_score?: number;
    traffic_light?: { status: string; risk_score: number };
  };
};

export type EnoIntakeChannelStatus = "present" | "missing";

export type EnoMultimodalIntakeSnapshot = {
  schema: "eno_multimodal_intake_snapshot_v1";
  captured_at: string;
  source: "eno_pwa" | "paste_json" | "local_storage";
  channels: {
    voice: EnoIntakeChannelStatus;
    tongue: EnoIntakeChannelStatus;
    survey: EnoIntakeChannelStatus;
    rppg: EnoIntakeChannelStatus;
  };
  vector_4d: { S: number; L: number; K: number; M: number };
  traffic_light: {
    status: "normal" | "caution" | "high_risk";
    risk_score: number;
    message: string;
    icon: string;
  };
  clinician_summary_ko: string;
  guardian_analysis_message?: string;
  disclaimer_ko: string;
};

function hasVoice(d: EnoHealthData): boolean {
  return Boolean(d.voice && (d.voice.jitter != null || d.voice.shimmer != null || d.voice.pitch != null));
}

function hasTongue(d: EnoHealthData): boolean {
  return Boolean(
    d.tongue &&
      (d.tongue.color || d.tongue.coating || d.tongue.hydrationScore != null || d.tongue.healthInsight),
  );
}

function hasSurvey(d: EnoHealthData): boolean {
  return Boolean(d.survey?.vector_4d || d.survey?.total_score != null);
}

function hasRppg(d: EnoHealthData): boolean {
  return Boolean(d.rppg && (d.rppg.heart_rate != null || d.rppg.stress_score != null));
}

export function convertEnoHealthTo4DVector(healthData: EnoHealthData): { S: number; L: number; K: number; M: number } {
  let S = 0.25;
  let L = 0.25;
  let K = 0.25;
  let M = 0.25;

  if (healthData.survey?.vector_4d) {
    return healthData.survey.vector_4d;
  }

  if (healthData.rppg) {
    const stress = healthData.rppg.stress_score ?? 50;
    const heartRate = healthData.rppg.heart_rate ?? 70;
    if (stress > 70) {
      S -= 0.1;
      M += 0.1;
    }
    if (heartRate < 60 || heartRate > 100) {
      M += 0.05;
    }
  }

  if (healthData.tongue) {
    const hydration = healthData.tongue.hydrationScore ?? 50;
    if (hydration < 50) M += 0.05;
    if (healthData.tongue.color === "Red" || healthData.tongue.color === "Purple") M += 0.05;
  }

  if (healthData.voice) {
    const jitter = healthData.voice.jitter ?? 0;
    const shimmer = healthData.voice.shimmer ?? 0;
    if (jitter > 0.5 || shimmer > 0.3) S -= 0.05;
  }

  const sum = S + L + K + M;
  return {
    S: Math.max(0, Math.min(1, S / sum)),
    L: Math.max(0, Math.min(1, L / sum)),
    K: Math.max(0, Math.min(1, K / sum)),
    M: Math.max(0, Math.min(1, M / sum)),
  };
}

export function calculateEnoTrafficLight(vector4d: { S: number; L: number; K: number; M: number }): {
  status: "normal" | "caution" | "high_risk";
  risk_score: number;
  message: string;
  icon: string;
} {
  const riskScore = vector4d.M;
  if (riskScore >= 0.7) {
    return {
      status: "high_risk",
      risk_score: riskScore,
      message: "주의 신호가 높습니다. 가능한 빠르게 한의사 상담을 권장합니다.",
      icon: "🔴",
    };
  }
  if (riskScore >= 0.5) {
    return {
      status: "caution",
      risk_score: riskScore,
      message: "주의가 필요한 상태입니다. 생활 관리 점검과 상담 준비를 권장합니다.",
      icon: "🟡",
    };
  }
  return {
    status: "normal",
    risk_score: riskScore,
    message: "현재 지표는 안정 범위입니다. 현재 관리 루틴을 유지해 보세요.",
    icon: "🟢",
  };
}

export function parseEnoHealthPayload(raw: unknown): { ok: true; data: EnoHealthData } | { ok: false; error: string } {
  if (!raw || typeof raw !== "object") {
    return { ok: false, error: "invalid_json_object" };
  }
  const obj = raw as Record<string, unknown>;
  const health =
    obj.health_data && typeof obj.health_data === "object"
      ? (obj.health_data as EnoHealthData)
      : (obj as EnoHealthData);
  if (!hasVoice(health) && !hasTongue(health) && !hasSurvey(health) && !hasRppg(health)) {
    return { ok: false, error: "empty_channels" };
  }
  return { ok: true, data: health };
}

function channelLabel(status: EnoIntakeChannelStatus): string {
  return status === "present" ? "수집됨" : "없음";
}

export function buildEnoClinicianSummaryKo(
  data: EnoHealthData,
  channels: EnoMultimodalIntakeSnapshot["channels"],
  vector4d: { S: number; L: number; K: number; M: number },
  traffic: EnoMultimodalIntakeSnapshot["traffic_light"],
): string {
  const parts: string[] = [
    `[엔오 관측·보조] 음성 ${channelLabel(channels.voice)} · 설진 ${channelLabel(channels.tongue)} · 설문 ${channelLabel(channels.survey)} · rPPG ${channelLabel(channels.rppg)}`,
    `4D S/L/K/M=${vector4d.S.toFixed(2)}/${vector4d.L.toFixed(2)}/${vector4d.K.toFixed(2)}/${vector4d.M.toFixed(2)} · 신호등 ${traffic.icon} ${traffic.status}`,
  ];
  if (data.rppg?.heart_rate != null) parts.push(`심박 ${data.rppg.heart_rate}bpm`);
  if (data.rppg?.stress_score != null) parts.push(`스트레스지수 ${data.rppg.stress_score}`);
  if (data.tongue?.color) parts.push(`설색 ${data.tongue.color}`);
  if (data.tongue?.hydrationScore != null) parts.push(`설진 수분 ${data.tongue.hydrationScore}`);
  if (data.voice?.jitter != null) parts.push(`음성 jitter ${data.voice.jitter}`);
  return parts.join(" · ");
}

export function buildEnoMultimodalIntakeSnapshot(
  data: EnoHealthData,
  source: EnoMultimodalIntakeSnapshot["source"],
  guardianAnalysisMessage?: string,
): EnoMultimodalIntakeSnapshot {
  const channels = {
    voice: hasVoice(data) ? "present" : "missing",
    tongue: hasTongue(data) ? "present" : "missing",
    survey: hasSurvey(data) ? "present" : "missing",
    rppg: hasRppg(data) ? "present" : "missing",
  } as const;
  const vector4d = convertEnoHealthTo4DVector(data);
  const traffic_light = calculateEnoTrafficLight(vector4d);
  return {
    schema: "eno_multimodal_intake_snapshot_v1",
    captured_at: new Date().toISOString(),
    source,
    channels,
    vector_4d: vector4d,
    traffic_light,
    clinician_summary_ko: buildEnoClinicianSummaryKo(data, channels, vector4d, traffic_light),
    ...(guardianAnalysisMessage?.trim() ? { guardian_analysis_message: guardianAnalysisMessage.trim() } : {}),
    disclaimer_ko:
      "엔오 자가측정·AI 초안입니다. 진단·처방·확정 4진은 한의사가 확인합니다. [보조·human_confirm]",
  };
}

export function applyEnoIntakeToClinicianNotes(
  existingFreeText: string,
  snapshot: EnoMultimodalIntakeSnapshot,
): string {
  const block = snapshot.clinician_summary_ko;
  const base = existingFreeText.trim();
  if (!base) return block;
  if (base.includes("[엔오 관측·보조]")) return base;
  return `${base}\n\n${block}`;
}
