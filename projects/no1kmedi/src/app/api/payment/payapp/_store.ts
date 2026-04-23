import { fileStoreAdapter } from "./_store.file";
import { postgresStoreAdapter } from "./_store.postgres";
import type { ClinicVerification, PayappPayment, PaymentStoreAdapter } from "./_store.types";

function resolveAdapter(): PaymentStoreAdapter {
  const driver = (process.env.NO1KMEDI_STORE_DRIVER || "file").trim().toLowerCase();
  if (driver === "file") return fileStoreAdapter;
  if (driver === "postgres") return postgresStoreAdapter;
  // Unknown value -> safe fallback.
  return fileStoreAdapter;
}

const adapter = resolveAdapter();

export async function getPayments(): Promise<PayappPayment[]> {
  return adapter.getPayments();
}

export async function savePayments(rows: PayappPayment[]): Promise<void> {
  await adapter.savePayments(rows);
}

export async function getVerifications(): Promise<ClinicVerification[]> {
  return adapter.getVerifications();
}

export async function saveVerifications(rows: ClinicVerification[]): Promise<void> {
  await adapter.saveVerifications(rows);
}
