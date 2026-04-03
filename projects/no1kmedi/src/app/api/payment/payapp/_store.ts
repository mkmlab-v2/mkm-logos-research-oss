import { promises as fs } from "fs";
import path from "path";

const DATA_DIR = path.join(process.cwd(), "memory", "commercialization");
const PAYMENTS_FILE = path.join(DATA_DIR, "payapp_payments.json");
const VERIFICATIONS_FILE = path.join(DATA_DIR, "clinic_verifications.json");

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

export type PayappPayment = {
  order_id: string;
  email: string;
  plan_code: string;
  amount?: number;
  state: "requested" | "pending" | "paid" | "failed";
  payapp_tid?: string;
  raw?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ClinicVerification = {
  id: string;
  email: string;
  clinic_name: string;
  biz_number: string;
  license_number: string;
  note?: string;
  status: "pending" | "approved" | "rejected";
  reviewed_by?: string;
  created_at: string;
  updated_at: string;
};

export async function getPayments(): Promise<PayappPayment[]> {
  return readJson<PayappPayment[]>(PAYMENTS_FILE, []);
}

export async function savePayments(rows: PayappPayment[]): Promise<void> {
  await writeJson(PAYMENTS_FILE, rows);
}

export async function getVerifications(): Promise<ClinicVerification[]> {
  return readJson<ClinicVerification[]>(VERIFICATIONS_FILE, []);
}

export async function saveVerifications(rows: ClinicVerification[]): Promise<void> {
  await writeJson(VERIFICATIONS_FILE, rows);
}
