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

export type PaymentStoreAdapter = {
  getPayments(): Promise<PayappPayment[]>;
  savePayments(rows: PayappPayment[]): Promise<void>;
  getVerifications(): Promise<ClinicVerification[]>;
  saveVerifications(rows: ClinicVerification[]): Promise<void>;
};
