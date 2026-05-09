import { promises as fs } from "fs";
import path from "path";

const DATA_DIR = path.join(process.cwd(), "memory", "commercialization");
const PRESURVEYS_FILE = path.join(DATA_DIR, "patient_presurveys.json");
const RESERVATIONS_FILE = path.join(DATA_DIR, "partner_reservations.json");

async function ensureDir() {
  await fs.mkdir(DATA_DIR, { recursive: true });
}

async function readJson<T>(filePath: string, fallback: T): Promise<T> {
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

async function writeJson<T>(filePath: string, data: T): Promise<void> {
  await ensureDir();
  await fs.writeFile(filePath, JSON.stringify(data, null, 2), "utf-8");
}

export type PatientPreSurveyRecord = {
  survey_id: string;
  intake_pin?: string;
  submitted_at_utc: string;
  status: "patient_submitted";
  triage_level: "routine" | "priority" | "emergency";
  patient: {
    name: string;
    phone: string;
    age_band: string;
  };
  symptoms: {
    pain_area: string;
    pain_scale_0_10: number;
    symptom_duration: string;
    consultation_goal: string;
  };
  reservation: {
    partner_clinic_preference: {
      region: string;
      specialty: string;
      preferred_time: string;
    };
  };
  lane_a_profile: {
    constitution_survey: {
      schema_version?: string;
      sleep_pattern: string;
      digestion_pattern: string;
      questionnaire_answers?: Record<string, string>;
    };
  };
  safety: {
    red_flags: {
      chestPain?: boolean;
      breathingTrouble?: boolean;
      paralysisOrSpeech?: boolean;
      highFeverOrBleeding?: boolean;
    };
  };
  consent: {
    privacy: boolean;
    medical: boolean;
  };
  meta?: {
    source?: string;
    kakao_summary?: Record<string, unknown>;
  };
};

export type PartnerReservationRecord = {
  reservation_request_id: string;
  requested_at_utc: string;
  status: "requested" | "contacted" | "booked" | "closed";
  survey_id: string;
  clinic_id: string;
  clinic_name: string;
  patient_name: string;
  patient_phone: string;
  updated_at_utc: string;
};

export async function getPreSurveys(): Promise<PatientPreSurveyRecord[]> {
  return readJson<PatientPreSurveyRecord[]>(PRESURVEYS_FILE, []);
}

export async function savePreSurveys(rows: PatientPreSurveyRecord[]): Promise<void> {
  await writeJson(PRESURVEYS_FILE, rows);
}

export async function getReservations(): Promise<PartnerReservationRecord[]> {
  return readJson<PartnerReservationRecord[]>(RESERVATIONS_FILE, []);
}

export async function saveReservations(rows: PartnerReservationRecord[]): Promise<void> {
  await writeJson(RESERVATIONS_FILE, rows);
}
