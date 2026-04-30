export type GuardianChatLane = "consumer" | "clinician";

export function resolveGuardianChatLane(value: unknown): GuardianChatLane {
  const v = typeof value === "string" ? value.trim().toLowerCase() : "";
  return v === "clinician" ? "clinician" : "consumer";
}

export function buildGuardianSystemInstruction(lane: GuardianChatLane): string {
  if (lane === "clinician") {
    return [
      "You are a Korean medicine clinician-assist copilot for licensed practitioners.",
      "Do not output definitive diagnosis or prescription orders.",
      "Provide concise, structured, evidence-oriented clinical-support reasoning in Korean.",
      "Always separate observed signals vs hypothesis vs next verification steps.",
    ].join(" ");
  }
  return [
    "You are a public pre-consultation assistant for Korean medicine.",
    "Do not diagnose and do not provide treatment decisions.",
    "Answer in simple Korean with short safety-first guidance.",
    "Always encourage in-person Korean medicine consultation and include clinic-connection guidance.",
  ].join(" ");
}

export function buildGuardianPrompt(
  lane: GuardianChatLane,
  payload: {
    vectorCoords: string;
    recentHistory: string;
    message: string;
  },
): string {
  if (lane === "clinician") {
    return [
      `Lane: clinician`,
      `4D: [${payload.vectorCoords}]`,
      `History: ${payload.recentHistory || "none"}`,
      `Question: ${payload.message}`,
      "Output format:",
      "1) 관찰 신호(요약)",
      "2) 임상 가설(우선순위 2개 이내)",
      "3) 확인 질문/검사 제안",
      "4) 안전 고지(확정 진단 아님)",
    ].join("\n");
  }
  return [
    `Lane: consumer`,
    `4D: [${payload.vectorCoords}]`,
    `History: ${payload.recentHistory || "none"}`,
    `Question: ${payload.message}`,
    "Output constraints:",
    "- 2~3문장 간단 통찰",
    "- 응급 경고 필요 시 즉시 병원/119 안내",
    "- 마지막 문장에 한의원 진찰/연결 권고 포함",
  ].join("\n");
}
