import { readFile } from 'fs/promises'
import path from 'path'
import { NextResponse } from 'next/server'

const HANDOFF_FILE = path.join(process.cwd(), 'public/data/jema_ai_hub_brand_handoff_v1.json')

export async function GET() {
  try {
    const raw = await readFile(HANDOFF_FILE, 'utf-8')
    return new NextResponse(raw, {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'public, max-age=300',
      },
    })
  } catch {
    return NextResponse.json({ error: 'handoff_missing', send_gate: 'HOLD' }, { status: 404 })
  }
}
