import fs from "node:fs";
import path from "node:path";

export type PatientIntakeSendGate = {
  send_gate: string;
  ready_for_external_send: boolean;
  ready_internal_poc: boolean;
};

const DEFAULT_GATE: PatientIntakeSendGate = {
  send_gate: "HOLD",
  ready_for_external_send: false,
  ready_internal_poc: false,
};

function gateFromDoc(doc: Record<string, unknown>): PatientIntakeSendGate {
  return {
    send_gate: String(doc.send_gate || "HOLD"),
    ready_for_external_send: Boolean(doc.ready_for_external_send),
    ready_internal_poc: Boolean(doc.ready_internal_poc),
  };
}

export function loadPatientIntakeSendGate(): PatientIntakeSendGate {
  const envOverride = process.env.PATIENT_INTAKE_SEND_GATE?.trim();
  if (envOverride) {
    return {
      send_gate: envOverride,
      ready_for_external_send: envOverride === "READY_EXTERNAL",
      ready_internal_poc: envOverride === "READY_INTERNAL_POC" || envOverride === "READY_EXTERNAL",
    };
  }

  const candidates = [
    process.env.PATIENT_INTAKE_SEND_GATE_PATH,
    path.join(process.cwd(), "memory/commercialization/patient_intake_send_gate_v1_latest.json"),
    path.join(process.cwd(), "../../docs/final/artifacts/patient_intake_send_gate_v1_latest.json"),
  ].filter((p): p is string => Boolean(p));

  for (const candidate of candidates) {
    try {
      if (!fs.existsSync(candidate)) continue;
      const doc = JSON.parse(fs.readFileSync(candidate, "utf8")) as Record<string, unknown>;
      return gateFromDoc(doc);
    } catch {
      // try next candidate
    }
  }

  return DEFAULT_GATE;
}

export function mayDeliverIntakeNotification(gate: PatientIntakeSendGate): {
  allowed: boolean;
  lane: "hold" | "internal_poc" | "external";
  reason?: string;
} {
  if (gate.ready_for_external_send) {
    return { allowed: true, lane: "external" };
  }
  if (gate.ready_internal_poc && gate.send_gate === "READY_INTERNAL_POC") {
    return { allowed: true, lane: "internal_poc" };
  }
  return {
    allowed: false,
    lane: "hold",
    reason: `send_gate=${gate.send_gate}`,
  };
}
