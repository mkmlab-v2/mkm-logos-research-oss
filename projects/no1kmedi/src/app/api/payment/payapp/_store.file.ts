import { promises as fs } from "fs";
import path from "path";
import type { ClinicVerification, PayappPayment, PaymentStoreAdapter } from "./_store.types";

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

export const fileStoreAdapter: PaymentStoreAdapter = {
  getPayments() {
    return readJson<PayappPayment[]>(PAYMENTS_FILE, []);
  },
  savePayments(rows) {
    return writeJson(PAYMENTS_FILE, rows);
  },
  getVerifications() {
    return readJson<ClinicVerification[]>(VERIFICATIONS_FILE, []);
  },
  saveVerifications(rows) {
    return writeJson(VERIFICATIONS_FILE, rows);
  },
};
