import type { ClinicianConsultFormState } from "@/lib/clinician-consult-payload-v1";

export type ClinicianChatRole = "user" | "assistant";

export type ClinicianChatTurn = {
  role: ClinicianChatRole;
  message: string;
};

export type PasteChartFusionContextV1 = {
  syncedAt: number;
  patientLabel: string;
  adviceTitles: string[];
  assessmentLine?: string;
  ephemeral?: boolean;
};

export type ClinicianThreadContext = ClinicianConsultFormState & {
  lensMode: "neutral" | "integrated" | "compare";
  includeScripture: boolean;
  /** Last Paste Chart analyze → chat thread fusion (Track B). */
  pasteChartFusion?: PasteChartFusionContextV1 | null;
};

export type ClinicianCdsSnapshot = {
  requestId: string;
  clinicalSummary: string;
  reasoning: { syndrome_hypothesis: string; care_direction: string; caution: string };
  envelope?: Record<string, unknown>;
  validationOk: boolean;
};

export type ClinicianChatThread = {
  id: string;
  title: string;
  /** User-edited display name (e.g. patient name). Shown in sidebar when set. */
  patientLabel?: string;
  /** Optional session date (YYYY-MM-DD) for sidebar grouping / labels. */
  sessionDate?: string;
  /** When true, auto-title from first user message is disabled. */
  titlePinned?: boolean;
  createdAt: number;
  updatedAt: number;
  turns: ClinicianChatTurn[];
  context: ClinicianThreadContext;
  lastCds?: ClinicianCdsSnapshot;
};

export type ClinicianThreadMetaPatch = {
  title?: string;
  patientLabel?: string;
  sessionDate?: string;
  titlePinned?: boolean;
};
