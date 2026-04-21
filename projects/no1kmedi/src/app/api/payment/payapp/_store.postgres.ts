import { Pool } from "pg";
import type { ClinicVerification, PaymentStoreAdapter, PayappPayment } from "./_store.types";

let pool: Pool | null = null;
let schemaReady: Promise<void> | null = null;

function readDatabaseUrl(): string {
  const url = (process.env.NO1KMEDI_POSTGRES_URL || process.env.DATABASE_URL || "").trim();
  if (!url) {
    throw new Error(
      "[payapp-store] NO1KMEDI_STORE_DRIVER=postgres requires NO1KMEDI_POSTGRES_URL (or DATABASE_URL).",
    );
  }
  return url;
}

function getPool(): Pool {
  if (!pool) {
    pool = new Pool({
      connectionString: readDatabaseUrl(),
      max: Number(process.env.NO1KMEDI_POSTGRES_POOL_MAX || 10),
    });
  }
  return pool;
}

async function ensureSchema(): Promise<void> {
  if (schemaReady) return schemaReady;
  schemaReady = (async () => {
    const p = getPool();
    await p.query(`
      CREATE TABLE IF NOT EXISTS no1kmedi_payments (
        order_id TEXT PRIMARY KEY,
        email TEXT NOT NULL,
        plan_code TEXT NOT NULL,
        amount INTEGER NULL,
        state TEXT NOT NULL,
        payapp_tid TEXT NULL,
        raw_json JSONB NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0
      )
    `);
    await p.query(`
      CREATE TABLE IF NOT EXISTS no1kmedi_verifications (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL,
        clinic_name TEXT NOT NULL,
        biz_number TEXT NOT NULL,
        license_number TEXT NOT NULL,
        note TEXT NULL,
        status TEXT NOT NULL,
        reviewed_by TEXT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0
      )
    `);
  })();
  return schemaReady;
}

function mapPayment(row: any): PayappPayment {
  return {
    order_id: row.order_id,
    email: row.email,
    plan_code: row.plan_code,
    amount: row.amount == null ? undefined : Number(row.amount),
    state: row.state,
    payapp_tid: row.payapp_tid ?? undefined,
    raw: row.raw_json ?? undefined,
    created_at: new Date(row.created_at).toISOString(),
    updated_at: new Date(row.updated_at).toISOString(),
  };
}

function mapVerification(row: any): ClinicVerification {
  return {
    id: row.id,
    email: row.email,
    clinic_name: row.clinic_name,
    biz_number: row.biz_number,
    license_number: row.license_number,
    note: row.note ?? undefined,
    status: row.status,
    reviewed_by: row.reviewed_by ?? undefined,
    created_at: new Date(row.created_at).toISOString(),
    updated_at: new Date(row.updated_at).toISOString(),
  };
}

export const postgresStoreAdapter: PaymentStoreAdapter = {
  async getPayments() {
    await ensureSchema();
    const p = getPool();
    const res = await p.query(
      `SELECT * FROM no1kmedi_payments ORDER BY sort_order ASC, updated_at DESC, created_at DESC`,
    );
    return res.rows.map(mapPayment);
  },

  async savePayments(rows) {
    await ensureSchema();
    const p = getPool();
    const client = await p.connect();
    try {
      await client.query("BEGIN");
      await client.query("DELETE FROM no1kmedi_payments");
      for (let i = 0; i < rows.length; i += 1) {
        const r = rows[i];
        await client.query(
          `INSERT INTO no1kmedi_payments
            (order_id, email, plan_code, amount, state, payapp_tid, raw_json, created_at, updated_at, sort_order)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8::timestamptz,$9::timestamptz,$10)`,
          [
            r.order_id,
            r.email,
            r.plan_code,
            r.amount ?? null,
            r.state,
            r.payapp_tid ?? null,
            r.raw ?? null,
            r.created_at,
            r.updated_at,
            i,
          ],
        );
      }
      await client.query("COMMIT");
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  },

  async getVerifications() {
    await ensureSchema();
    const p = getPool();
    const res = await p.query(
      `SELECT * FROM no1kmedi_verifications ORDER BY sort_order ASC, updated_at DESC, created_at DESC`,
    );
    return res.rows.map(mapVerification);
  },

  async saveVerifications(rows) {
    await ensureSchema();
    const p = getPool();
    const client = await p.connect();
    try {
      await client.query("BEGIN");
      await client.query("DELETE FROM no1kmedi_verifications");
      for (let i = 0; i < rows.length; i += 1) {
        const r = rows[i];
        await client.query(
          `INSERT INTO no1kmedi_verifications
            (id, email, clinic_name, biz_number, license_number, note, status, reviewed_by, created_at, updated_at, sort_order)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::timestamptz,$10::timestamptz,$11)`,
          [
            r.id,
            r.email,
            r.clinic_name,
            r.biz_number,
            r.license_number,
            r.note ?? null,
            r.status,
            r.reviewed_by ?? null,
            r.created_at,
            r.updated_at,
            i,
          ],
        );
      }
      await client.query("COMMIT");
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  },
};

