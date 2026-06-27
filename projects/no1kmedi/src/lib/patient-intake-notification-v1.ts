import { deliverKakaoIntakeSummary, type KakaoDeliveryResult } from "@/lib/kakao-intake-adapter";
import {
  loadPatientIntakeSendGate,
  mayDeliverIntakeNotification,
  type PatientIntakeSendGate,
} from "@/lib/patient-intake-send-gate-v1";

export type IntakeNotificationDelivery = {
  gate: PatientIntakeSendGate;
  policy: ReturnType<typeof mayDeliverIntakeNotification>;
  kakao_delivery: KakaoDeliveryResult & { skipped_reason?: string };
};

function resolveIntakeWebhookUrl(): string {
  return (
    process.env.KAKAO_CLINIC_INTAKE_WEBHOOK_URL?.trim() ||
    process.env.PATIENT_INTAKE_SOLAPI_TEST_WEBHOOK_URL?.trim() ||
    ""
  );
}

export async function deliverClinicIntakeNotifications(input: {
  kakaoSummary: Record<string, unknown>;
}): Promise<IntakeNotificationDelivery> {
  const gate = loadPatientIntakeSendGate();
  const policy = mayDeliverIntakeNotification(gate);

  if (!policy.allowed) {
    return {
      gate,
      policy,
      kakao_delivery: {
        enabled: false,
        delivered: false,
        skipped_reason: policy.reason || "send_gate_hold",
      },
    };
  }

  const webhookUrl = resolveIntakeWebhookUrl();
  if (!webhookUrl) {
    return {
      gate,
      policy,
      kakao_delivery: {
        enabled: false,
        delivered: false,
        skipped_reason: "no_webhook_configured",
      },
    };
  }

  const kakao_delivery = await deliverKakaoIntakeSummary(webhookUrl, {
    ...input.kakaoSummary,
    notification_lane: policy.lane,
    send_gate: gate.send_gate,
  });

  return { gate, policy, kakao_delivery };
}
